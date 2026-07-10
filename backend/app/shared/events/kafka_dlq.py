"""
Kafka DLQ — dead-letter queue para eventos Kafka incompatíveis (CF-19).
"""
import enum
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.base import Base
from app.db.enum_column import enum_values

logger = get_logger("kafka_dlq")


class DlqReason(str, enum.Enum):
    """Motivo de envio para dead-letter queue."""

    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    AVRO_DECODE_ERROR = "avro_decode_error"
    ENVELOPE_PARSE_ERROR = "envelope_parse_error"
    HANDLER_ERROR = "handler_error"
    UNKNOWN = "unknown"


class CoreEventDlq(Base):
    """
    Registro persistente de mensagens Kafka enviadas à DLQ.

    Attributes:
        id: Identificador interno.
        source_topic: Tópico Kafka de origem.
        raw_payload: Payload serializado (JSON ou base64).
        error_type: Categoria do erro (DlqReason).
        error_message: Detalhe da falha.
        event_type: Tipo inferido do evento, se disponível.
        partition: Partição Kafka de origem.
        offset: Offset Kafka de origem.
        replayed_at: Timestamp de replay bem-sucedido, se houver.
    """

    __tablename__ = "core_event_dlq"

    id = Column(Integer, primary_key=True, index=True)
    source_topic = Column(String, nullable=False, index=True)
    raw_payload = Column(Text, nullable=False)
    error_type = Column(enum_values(DlqReason), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    event_type = Column(String, nullable=True, index=True)
    partition = Column(Integer, nullable=True)
    offset = Column(Integer, nullable=True)
    replay_attempts = Column(Integer, default=0, nullable=False)
    next_replay_at = Column(DateTime(timezone=True), nullable=True)
    last_replay_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    replayed_at = Column(DateTime(timezone=True), nullable=True)


class KafkaDlqService:
    """
    Persiste e publica mensagens incompatíveis na DLQ Kafka + banco local.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db

    def record(
        self,
        raw_payload: Any,
        error: Exception,
        reason: DlqReason = DlqReason.UNKNOWN,
        source_topic: Optional[str] = None,
        event_type: Optional[str] = None,
        partition: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> CoreEventDlq:
        """
        Grava mensagem na DLQ local e publica no tópico Kafka DLQ.

        Args:
            raw_payload: Payload original (dict, bytes ou str).
            error: Exceção que causou o envio à DLQ.
            reason: Categoria do erro.
            source_topic: Tópico de origem.
            event_type: Tipo do evento, se conhecido.
            partition: Partição Kafka.
            offset: Offset Kafka.

        Returns:
            Registro CoreEventDlq persistido.
        """
        serialized = self._serialize_payload(raw_payload)
        row = CoreEventDlq(
            source_topic=source_topic or settings.KAFKA_TOPIC,
            raw_payload=serialized,
            error_type=reason,
            error_message=str(error)[:2000],
            event_type=event_type,
            partition=partition,
            offset=offset,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        if settings.KAFKA_DLQ_ENABLED:
            self._publish_to_kafka(row)

        logger.warning(
            f"[dlq] Registrado id={row.id} reason={reason.value} event_type={event_type}"
        )
        return row

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Lista entradas DLQ mais recentes.

        Args:
            limit: Máximo de registros.

        Returns:
            Lista de dicts com metadados DLQ.
        """
        rows = (
            self.db.query(CoreEventDlq)
            .order_by(CoreEventDlq.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_dict(row) for row in rows]

    def stats(self) -> Dict[str, Any]:
        """
        Estatísticas agregadas da DLQ.

        Returns:
            Dict com total, por reason e pendentes de replay.
        """
        rows = self.db.query(CoreEventDlq).all()
        by_reason: Dict[str, int] = {}
        pending_replay = 0
        eligible_now = 0
        now = datetime.utcnow()
        for row in rows:
            key = row.error_type.value if hasattr(row.error_type, "value") else str(row.error_type)
            by_reason[key] = by_reason.get(key, 0) + 1
            if row.replayed_at is None:
                pending_replay += 1
                if row.next_replay_at is None or row.next_replay_at <= now:
                    eligible_now += 1
        return {
            "total": len(rows),
            "by_reason": by_reason,
            "pending_replay": pending_replay,
            "eligible_now": eligible_now,
            "dlq_topic": settings.KAFKA_DLQ_TOPIC,
            "enabled": settings.KAFKA_DLQ_ENABLED,
            "auto_replay_enabled": settings.KAFKA_DLQ_REPLAY_ENABLED,
        }

    def mark_replayed(self, dlq_id: int) -> Optional[CoreEventDlq]:
        """
        Marca entrada DLQ como replayed.

        Args:
            dlq_id: ID do registro DLQ.

        Returns:
            Registro atualizado ou None.
        """
        row = self.db.query(CoreEventDlq).filter(CoreEventDlq.id == dlq_id).first()
        if not row:
            return None
        row.replayed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row

    def _publish_to_kafka(self, row: CoreEventDlq) -> None:
        """
        Publica envelope DLQ no tópico Kafka dedicado.

        Args:
            row: Registro DLQ persistido.

        Returns:
            None
        """
        try:
            from app.shared.events.kafka_adapter import get_kafka_adapter

            adapter = get_kafka_adapter()
            envelope = {
                "dlq_id": row.id,
                "source_topic": row.source_topic,
                "error_type": row.error_type.value if hasattr(row.error_type, "value") else row.error_type,
                "error_message": row.error_message,
                "event_type": row.event_type,
                "raw_payload": row.raw_payload,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            producer = adapter._get_producer()
            future = producer.send(settings.KAFKA_DLQ_TOPIC, envelope)
            future.get(timeout=10)
        except Exception as exc:
            logger.error(f"[dlq] Falha publicar no Kafka DLQ: {exc}")

    @staticmethod
    def _serialize_payload(raw_payload: Any) -> str:
        """
        Serializa payload bruto para armazenamento.

        Args:
            raw_payload: dict, bytes ou str.

        Returns:
            String JSON ou texto.
        """
        if isinstance(raw_payload, bytes):
            import base64

            return json.dumps({"encoding": "base64", "data": base64.b64encode(raw_payload).decode()})
        if isinstance(raw_payload, dict):
            return json.dumps(raw_payload, default=str)
        return str(raw_payload)

    @staticmethod
    def _to_dict(row: CoreEventDlq) -> Dict[str, Any]:
        """
        Converte registro ORM em dict API-safe.

        Args:
            row: Registro CoreEventDlq.

        Returns:
            Dict serializável.
        """
        return {
            "id": row.id,
            "source_topic": row.source_topic,
            "error_type": row.error_type.value if hasattr(row.error_type, "value") else row.error_type,
            "error_message": row.error_message,
            "event_type": row.event_type,
            "partition": row.partition,
            "offset": row.offset,
            "replay_attempts": row.replay_attempts or 0,
            "next_replay_at": row.next_replay_at.isoformat() if row.next_replay_at else None,
            "last_replay_error": row.last_replay_error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "replayed_at": row.replayed_at.isoformat() if row.replayed_at else None,
        }
