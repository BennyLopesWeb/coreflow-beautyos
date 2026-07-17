"""
Outbox pattern — persistência de eventos de domínio antes da publicação.

Preparado para worker assíncrono (RabbitMQ/Kafka); no monólito publica
sincronamente após persistir.

R2-F2: ``defer_commit`` permite TX única handler + outbox + idempotency (TD-R2-F1b-001).
"""
import enum
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.logging_config import get_logger
from app.db.base import Base
from app.db.enum_column import enum_values
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus

logger = get_logger("outbox")


class OutboxStatus(str, enum.Enum):
    """Status de processamento de um evento outbox."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class CoreEventOutbox(Base):
    """
    Fila persistente de eventos de domínio (Outbox pattern).

    Attributes:
        id: Identificador interno.
        event_id: UUID do evento.
        event_type: Tipo (ex.: booking.created).
        company_id: Tenant.
        aggregate_id: ID da entidade raiz.
        aggregate_type: Tipo da entidade raiz.
        payload: JSON serializado.
        status: pending | processed | failed.
        error_message: Detalhe de falha opcional.
    """

    __tablename__ = "core_event_outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(255), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    aggregate_id = Column(String(255), nullable=True, index=True)
    aggregate_type = Column(String(255), nullable=True)
    payload = Column(Text, nullable=False)
    status = Column(
        enum_values(OutboxStatus),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


@dataclass
class OutboxBatch:
    """
    Acumula eventos outbox para commit único + publicação pós-commit (R2-F2).

    Attributes:
        db: Sessão SQLAlchemy.
        _entries: Pares (row outbox, DomainEvent) registrados com defer_commit.
    """

    db: Session
    _entries: List[Tuple[CoreEventOutbox, DomainEvent]] = field(default_factory=list)

    def record(self, event: DomainEvent) -> CoreEventOutbox:
        """
        Registra evento na TX corrente sem commit.

        Args:
            event: Evento de domínio.

        Returns:
            Linha outbox PENDING.
        """
        row = OutboxService(self.db).record(event, defer_commit=True)
        self._entries.append((row, event))
        return row

    def publish_after_commit(self) -> None:
        """
        Publica eventos no bus após commit da TX principal.

        Returns:
            None

        Raises:
            Exception: Falha de publicação — marca outbox failed.
        """
        if self._entries:
            OutboxService(self.db).finalize_sync(self._entries)


class OutboxService:
    """
    Grava eventos no outbox e publica no bus in-memory.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _envelope_payload(event: DomainEvent) -> Dict[str, Any]:
        """
        Monta payload outbox com correlation_id no envelope (ADR-027 / F1b).

        Args:
            event: Evento de domínio.

        Returns:
            Dict serializável para coluna payload.
        """
        data = dict(event.payload)
        if event.correlation_id:
            data["correlation_id"] = event.correlation_id
        return data

    def record(self, event: DomainEvent, *, defer_commit: bool = False) -> CoreEventOutbox:
        """
        Persiste evento no outbox.

        Args:
            event: Evento de domínio.
            defer_commit: Se True, apenas flush — commit fica com handler (R2-F2).

        Returns:
            Registro outbox.
        """
        row = CoreEventOutbox(
            event_id=event.event_id,
            event_type=event.event_type,
            company_id=event.company_id,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            payload=json.dumps(self._envelope_payload(event), default=str),
            status=OutboxStatus.PENDING,
        )
        self.db.add(row)
        self.db.flush()
        if defer_commit:
            from app.core.architecture_metrics import ArchitectureMetricsStore

            ArchitectureMetricsStore.get().record_outbox_defer_commit()
            return row
        return self._finalize_row(row, event)

    def record_and_publish(self, event: DomainEvent, *, defer_commit: bool = False) -> CoreEventOutbox:
        """
        Persiste evento e publica conforme ``OUTBOX_DISPATCH_MODE``.

        Args:
            event: Evento de domínio.
            defer_commit: Delega commit à camada superior quando True.

        Returns:
            Registro outbox.
        """
        if defer_commit:
            return self.record(event, defer_commit=True)
        return self.record(event, defer_commit=False)

    def finalize_sync(self, entries: List[Tuple[CoreEventOutbox, DomainEvent]]) -> None:
        """
        Publica eventos sync-mode após commit externo e marca processed.

        Args:
            entries: Pares (row, event) registrados com defer_commit.

        Returns:
            None
        """
        from app.core.config import settings

        mode = (settings.OUTBOX_DISPATCH_MODE or "sync").lower()
        if mode in ("deferred",) or (
            mode == "rabbitmq" and settings.RABBITMQ_ENABLED
        ) or (mode == "kafka" and settings.KAFKA_ENABLED):
            return

        for row, event in entries:
            try:
                event_bus.publish(event)
                row.status = OutboxStatus.PROCESSED
                row.processed_at = datetime.utcnow()
            except Exception as exc:
                row.status = OutboxStatus.FAILED
                row.error_message = str(exc)[:2000]
                self.db.commit()
                logger.error(f"Outbox publish failed: {event.event_type} — {exc}")
                raise
        if entries:
            self.db.commit()

    def _finalize_row(self, row: CoreEventOutbox, event: DomainEvent) -> CoreEventOutbox:
        """
        Publica e commita um único evento (comportamento legado pré-F2).

        Args:
            row: Linha outbox PENDING.
            event: Evento associado.

        Returns:
            Registro outbox atualizado.
        """
        from app.core.config import settings

        mode = (settings.OUTBOX_DISPATCH_MODE or "sync").lower()

        if mode == "rabbitmq" and settings.RABBITMQ_ENABLED:
            try:
                from app.shared.events.rabbitmq_adapter import get_rabbitmq_adapter

                get_rabbitmq_adapter().publish(event, outbox_id=row.id)
                self.db.commit()
                return row
            except Exception as exc:
                row.status = OutboxStatus.FAILED
                row.error_message = str(exc)[:2000]
                logger.error(f"Outbox rabbitmq failed: {event.event_type} — {exc}")
                self.db.commit()
                raise

        if mode == "kafka" and settings.KAFKA_ENABLED:
            try:
                from app.shared.events.kafka_adapter import get_kafka_adapter

                get_kafka_adapter().publish(event, outbox_id=row.id)
                self.db.commit()
                return row
            except Exception as exc:
                row.status = OutboxStatus.FAILED
                row.error_message = str(exc)[:2000]
                logger.error(f"Outbox kafka failed: {event.event_type} — {exc}")
                self.db.commit()
                raise

        if mode == "deferred":
            self.db.commit()
            return row

        try:
            event_bus.publish(event)
            row.status = OutboxStatus.PROCESSED
            row.processed_at = datetime.utcnow()
            self.db.commit()
        except Exception as exc:
            row.status = OutboxStatus.FAILED
            row.error_message = str(exc)[:2000]
            self.db.commit()
            logger.error(f"Outbox publish failed: {event.event_type} — {exc}")
            raise
        return row

    def list_pending(self, limit: int = 100) -> List[CoreEventOutbox]:
        """
        Lista eventos pendentes (para worker futuro).

        Args:
            limit: Máximo de registros.

        Returns:
            Lista de CoreEventOutbox pendentes.
        """
        return (
            self.db.query(CoreEventOutbox)
            .filter(CoreEventOutbox.status == OutboxStatus.PENDING)
            .order_by(CoreEventOutbox.id.asc())
            .limit(limit)
            .all()
        )

    def replay_pending(self) -> int:
        """
        Reprocessa eventos pendentes publicando no bus.

        Returns:
            Quantidade processada com sucesso.
        """
        pending = self.list_pending()
        count = 0
        for row in pending:
            try:
                event = self._to_domain_event(row)
                event_bus.publish(event)
                row.status = OutboxStatus.PROCESSED
                row.processed_at = datetime.utcnow()
                count += 1
            except Exception as exc:
                row.status = OutboxStatus.FAILED
                row.error_message = str(exc)[:2000]
        if pending:
            self.db.commit()
        return count

    def _to_domain_event(self, row: CoreEventOutbox) -> DomainEvent:
        """
        Reconstrói DomainEvent a partir do registro outbox.

        Args:
            row: Registro persistido.

        Returns:
            DomainEvent.
        """
        payload: Dict[str, Any] = json.loads(row.payload)
        correlation_id = payload.pop("correlation_id", None)
        return DomainEvent(
            event_id=row.event_id,
            event_type=row.event_type,
            company_id=row.company_id,
            payload=payload,
            aggregate_id=row.aggregate_id,
            aggregate_type=row.aggregate_type,
            correlation_id=correlation_id,
            occurred_at=row.created_at or datetime.utcnow(),
        )
