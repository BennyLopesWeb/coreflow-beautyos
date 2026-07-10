"""
KafkaDlqReplayService — replay automático DLQ com backoff exponencial (CF-20).
"""
import json
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.dlq_replay_metrics import record_dlq_replay_status, refresh_gauges_after_batch
from app.shared.events.kafka_dlq import CoreEventDlq, KafkaDlqService

logger = get_logger("kafka_dlq_replay")


class KafkaDlqReplayService:
    """
    Reprocessa mensagens DLQ pendentes com backoff exponencial.

    Attributes:
        db: Sessão SQLAlchemy.
        dlq: Serviço base DLQ.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db
        self.dlq = KafkaDlqService(db)

    @staticmethod
    def calculate_backoff_seconds(attempts: int) -> int:
        """
        Calcula delay exponencial entre tentativas de replay.

        Args:
            attempts: Número de tentativas já realizadas.

        Returns:
            Segundos até próximo replay (cap em max configurado).
        """
        base = settings.KAFKA_DLQ_REPLAY_BACKOFF_BASE_SECONDS
        maximum = settings.KAFKA_DLQ_REPLAY_BACKOFF_MAX_SECONDS
        return min(base * (2 ** max(attempts, 0)), maximum)

    def list_eligible(self, limit: int = 20) -> List[CoreEventDlq]:
        """
        Lista entradas DLQ elegíveis para replay automático.

        Args:
            limit: Máximo de registros.

        Returns:
            Rows com replayed_at nulo e next_replay_at vencido/ausente.
        """
        now = datetime.utcnow()
        query = (
            self.db.query(CoreEventDlq)
            .filter(CoreEventDlq.replayed_at.is_(None))
            .filter(
                (CoreEventDlq.next_replay_at.is_(None))
                | (CoreEventDlq.next_replay_at <= now)
            )
        )
        if settings.KAFKA_DLQ_REPLAY_MAX_ATTEMPTS > 0:
            query = query.filter(
                CoreEventDlq.replay_attempts < settings.KAFKA_DLQ_REPLAY_MAX_ATTEMPTS
            )
        return query.order_by(CoreEventDlq.created_at.asc()).limit(limit).all()

    def replay_one(self, dlq_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Tenta republicar uma mensagem DLQ no tópico principal.

        Args:
            dlq_id: ID do registro DLQ.
            force: Ignorar backoff/next_replay_at.

        Returns:
            Dict com status success|scheduled|failed|skipped.

        Raises:
            ValueError: Registro não encontrado.
        """
        row = self.db.query(CoreEventDlq).filter(CoreEventDlq.id == dlq_id).first()
        if not row:
            raise ValueError(f"DLQ id={dlq_id} não encontrado")
        if row.replayed_at is not None:
            record_dlq_replay_status("republish", "skipped")
            return {"dlq_id": dlq_id, "status": "skipped", "reason": "already_replayed"}

        now = datetime.utcnow()
        if (
            not force
            and row.next_replay_at is not None
            and row.next_replay_at > now
        ):
            record_dlq_replay_status("republish", "scheduled")
            return {
                "dlq_id": dlq_id,
                "status": "scheduled",
                "next_replay_at": row.next_replay_at.isoformat(),
            }

        started = time.perf_counter()
        try:
            payload = self._deserialize_payload(row.raw_payload)
            self._publish_to_main_topic(payload, row.source_topic)
            row.replayed_at = now
            row.last_replay_error = None
            self.db.commit()
            duration = time.perf_counter() - started
            record_dlq_replay_status("republish", "success", duration)
            logger.info(f"[dlq-replay] Sucesso id={dlq_id}")
            return {"dlq_id": dlq_id, "status": "success", "replayed_at": row.replayed_at.isoformat()}
        except Exception as exc:
            duration = time.perf_counter() - started
            record_dlq_replay_status("republish", "failed", duration)
            row.replay_attempts = (row.replay_attempts or 0) + 1
            row.last_replay_error = str(exc)[:2000]
            delay = self.calculate_backoff_seconds(row.replay_attempts)
            row.next_replay_at = now + timedelta(seconds=delay)
            self.db.commit()
            logger.warning(
                f"[dlq-replay] Falha id={dlq_id} attempt={row.replay_attempts} "
                f"next_in={delay}s: {exc}"
            )
            return {
                "dlq_id": dlq_id,
                "status": "failed",
                "attempts": row.replay_attempts,
                "next_replay_at": row.next_replay_at.isoformat(),
                "error": str(exc),
            }

    def replay_batch(self, limit: int = 20, force: bool = False) -> Dict[str, Any]:
        """
        Executa replay automático em lote para entradas elegíveis.

        Args:
            limit: Máximo de mensagens por batch.
            force: Ignorar backoff.

        Returns:
            Resumo com success, failed e scheduled counts.
        """
        if not settings.KAFKA_DLQ_REPLAY_ENABLED:
            return {"enabled": False, "processed": 0, "results": []}

        eligible = self.list_eligible(limit=limit)
        results = []
        counts = {"success": 0, "failed": 0, "scheduled": 0, "skipped": 0}

        for row in eligible:
            result = self.replay_one(row.id, force=force)
            results.append(result)
            status = result.get("status", "failed")
            counts[status] = counts.get(status, 0) + 1

        result = {
            "enabled": True,
            "processed": len(results),
            "counts": counts,
            "results": results,
        }
        refresh_gauges_after_batch(self.db)
        return result

    def _publish_to_main_topic(self, payload: Any, topic: Optional[str] = None) -> None:
        """
        Republica payload no tópico Kafka principal.

        Args:
            payload: Dict ou bytes da mensagem original.
            topic: Tópico destino (default settings.KAFKA_TOPIC).

        Returns:
            None
        """
        from app.shared.events.kafka_adapter import get_kafka_adapter

        adapter = get_kafka_adapter()
        target_topic = topic or settings.KAFKA_TOPIC
        producer = adapter._get_producer()
        future = producer.send(target_topic, payload)
        future.get(timeout=10)

    @staticmethod
    def _deserialize_payload(raw: str) -> Any:
        """
        Deserializa payload armazenado na DLQ.

        Args:
            raw: String JSON persistida.

        Returns:
            dict ou bytes original.
        """
        import base64

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        if isinstance(parsed, dict) and parsed.get("encoding") == "base64":
            return base64.b64decode(parsed["data"])
        return parsed
