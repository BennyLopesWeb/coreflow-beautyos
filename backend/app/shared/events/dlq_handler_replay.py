"""
DlqHandlerReplay — reprocessamento handler-aware de mensagens DLQ (CF-21).

Republica eventos via event_bus (mesmo fluxo do outbox worker) em vez de
apenas reenviar bytes ao tópico Kafka.
"""
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.dlq_replay_metrics import record_dlq_replay_status, refresh_gauges_after_batch
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus
from app.shared.events.kafka_dlq import CoreEventDlq
from app.shared.events.kafka_dlq_replay import KafkaDlqReplayService
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus

logger = get_logger("dlq_handler_replay")


class DlqHandlerReplayService(KafkaDlqReplayService):
    """
    Estende replay DLQ executando handlers in-process (event_bus).

    Modo ``handler`` parseia envelope, publica no bus e confirma outbox
    quando ``outbox_id`` está presente na mensagem original.
    """

    def replay_one(
        self,
        dlq_id: int,
        force: bool = False,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Replay de mensagem DLQ com modo configurável.

        Args:
            dlq_id: ID do registro DLQ.
            force: Ignorar backoff/next_replay_at.
            mode: ``republish`` | ``handler`` (default settings).

        Returns:
            Dict com status e detalhes do replay.
        """
        replay_mode = mode or settings.KAFKA_DLQ_REPLAY_MODE
        if replay_mode == "handler":
            return self.replay_via_handler(dlq_id, force=force)
        result = super().replay_one(dlq_id, force=force)
        return {**result, "mode": "republish"}

    def replay_via_handler(self, dlq_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Reprocessa mensagem DLQ via event_bus (handler-aware).

        Args:
            dlq_id: ID do registro DLQ.
            force: Ignorar backoff.

        Returns:
            Dict com status success|failed|scheduled|skipped.

        Raises:
            ValueError: Registro não encontrado.
        """
        row = self.db.query(CoreEventDlq).filter(CoreEventDlq.id == dlq_id).first()
        if not row:
            raise ValueError(f"DLQ id={dlq_id} não encontrado")
        if row.replayed_at is not None:
            record_dlq_replay_status("handler", "skipped")
            return {"dlq_id": dlq_id, "status": "skipped", "reason": "already_replayed", "mode": "handler"}

        now = datetime.utcnow()
        if not force and row.next_replay_at is not None and row.next_replay_at > now:
            record_dlq_replay_status("handler", "scheduled")
            return {
                "dlq_id": dlq_id,
                "status": "scheduled",
                "mode": "handler",
                "next_replay_at": row.next_replay_at.isoformat(),
            }

        started = time.perf_counter()
        try:
            payload = self._deserialize_payload(row.raw_payload)
            event, outbox_id = self._parse_to_domain_event(payload)
            event_bus.publish(event)
            if outbox_id is not None:
                self._mark_outbox_processed(outbox_id)
            row.replayed_at = now
            row.last_replay_error = None
            self.db.commit()
            duration = time.perf_counter() - started
            record_dlq_replay_status("handler", "success", duration)
            logger.info(
                f"[dlq-handler] Sucesso id={dlq_id} event={event.event_type} outbox={outbox_id}"
            )
            return {
                "dlq_id": dlq_id,
                "status": "success",
                "mode": "handler",
                "event_type": event.event_type,
                "outbox_id": outbox_id,
                "replayed_at": row.replayed_at.isoformat(),
            }
        except Exception as exc:
            duration = time.perf_counter() - started
            record_dlq_replay_status("handler", "failed", duration)
            return self._schedule_retry(row, dlq_id, exc, mode="handler")

    def replay_batch(
        self,
        limit: int = 20,
        force: bool = False,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executa batch de replay com modo handler ou republish.

        Args:
            limit: Máximo de mensagens.
            force: Ignorar backoff.
            mode: republish | handler.

        Returns:
            Resumo do batch.
        """
        if not settings.KAFKA_DLQ_REPLAY_ENABLED:
            return {"enabled": False, "processed": 0, "results": [], "mode": mode}

        replay_mode = mode or settings.KAFKA_DLQ_REPLAY_MODE
        eligible = self.list_eligible(limit=limit)
        results = []
        counts = {"success": 0, "failed": 0, "scheduled": 0, "skipped": 0}

        for row in eligible:
            result = self.replay_one(row.id, force=force, mode=replay_mode)
            results.append(result)
            status = result.get("status", "failed")
            counts[status] = counts.get(status, 0) + 1

        result = {
            "enabled": True,
            "mode": replay_mode,
            "processed": len(results),
            "counts": counts,
            "results": results,
        }
        refresh_gauges_after_batch(self.db)
        return result

    def _parse_to_domain_event(self, payload: Any) -> Tuple[DomainEvent, Optional[int]]:
        """
        Converte payload DLQ em DomainEvent + outbox_id.

        Args:
            payload: Dict ou estrutura legada.

        Returns:
            Tupla (DomainEvent, outbox_id).

        Raises:
            ValueError: Payload inválido.
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload handler-aware requer dict JSON")

        if settings.KAFKA_SCHEMA_REGISTRY_ENABLED and "schema_id" in payload:
            from app.shared.events.schema_registry import get_schema_registry

            return get_schema_registry().parse_envelope(payload)

        if "event" in payload:
            from datetime import datetime as dt

            event_data = payload["event"]
            occurred = event_data.get("occurred_at")
            event = DomainEvent(
                event_id=event_data["event_id"],
                event_type=event_data["event_type"],
                company_id=event_data["company_id"],
                payload=event_data["payload"],
                aggregate_id=event_data.get("aggregate_id"),
                aggregate_type=event_data.get("aggregate_type"),
                occurred_at=dt.fromisoformat(occurred) if occurred else dt.utcnow(),
            )
            return event, payload.get("outbox_id")

        raise ValueError("Envelope DLQ não reconhecido para handler replay")

    def _mark_outbox_processed(self, outbox_id: int) -> None:
        """
        Marca outbox associado como processado após handler replay.

        Args:
            outbox_id: ID em core_event_outbox.

        Returns:
            None
        """
        row = self.db.query(CoreEventOutbox).filter(CoreEventOutbox.id == outbox_id).first()
        if row:
            row.status = OutboxStatus.PROCESSED
            row.processed_at = datetime.utcnow()
            self.db.commit()

    def _schedule_retry(
        self,
        row: CoreEventDlq,
        dlq_id: int,
        exc: Exception,
        mode: str,
    ) -> Dict[str, Any]:
        """
        Agenda nova tentativa após falha de replay.

        Args:
            row: Registro DLQ ORM.
            dlq_id: ID do registro.
            exc: Exceção capturada.
            mode: Modo de replay usado.

        Returns:
            Dict status failed com next_replay_at.
        """
        from datetime import timedelta

        now = datetime.utcnow()
        row.replay_attempts = (row.replay_attempts or 0) + 1
        row.last_replay_error = str(exc)[:2000]
        delay = self.calculate_backoff_seconds(row.replay_attempts)
        row.next_replay_at = now + timedelta(seconds=delay)
        self.db.commit()
        logger.warning(f"[dlq-{mode}] Falha id={dlq_id}: {exc}")
        return {
            "dlq_id": dlq_id,
            "status": "failed",
            "mode": mode,
            "attempts": row.replay_attempts,
            "next_replay_at": row.next_replay_at.isoformat(),
            "error": str(exc),
        }
