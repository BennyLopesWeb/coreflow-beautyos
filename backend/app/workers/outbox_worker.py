"""
OutboxWorker — processa eventos pendentes (poll DB ou consume RabbitMQ) CF-13.
"""
import argparse
import time
from datetime import datetime

from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus
from app.shared.events.outbox import CoreEventOutbox, OutboxService, OutboxStatus

logger = get_logger("outbox_worker")


def _mark_outbox_processed(outbox_id: int) -> None:
    """
    Marca registro outbox como processado após consumo RabbitMQ.

    Args:
        outbox_id: ID em core_event_outbox.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        row = db.query(CoreEventOutbox).filter(CoreEventOutbox.id == outbox_id).first()
        if row:
            row.status = OutboxStatus.PROCESSED
            row.processed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def _handle_event(event: DomainEvent, outbox_id: Optional[int] = None) -> None:
    """
    Publica evento no bus e confirma outbox se aplicável.

    Args:
        event: Evento de domínio.
        outbox_id: ID outbox para ack (modo RabbitMQ).

    Returns:
        None
    """
    event_bus.publish(event)
    if outbox_id is not None:
        _mark_outbox_processed(outbox_id)
    logger.info(f"[worker] Processado {event.event_type} outbox_id={outbox_id}")


def run_poll_once(limit: int = 100) -> int:
    """
    Reprocessa eventos pendentes do outbox (modo poll).

    Args:
        limit: Máximo de eventos por ciclo.

    Returns:
        Quantidade processada.
    """
    db = SessionLocal()
    try:
        service = OutboxService(db)
        pending = service.list_pending(limit=limit)
        count = 0
        for row in pending:
            try:
                event = service._to_domain_event(row)
                event_bus.publish(event)
                row.status = OutboxStatus.PROCESSED
                row.processed_at = datetime.utcnow()
                count += 1
            except Exception as exc:
                row.status = OutboxStatus.FAILED
                row.error_message = str(exc)[:2000]
                logger.error(f"[worker] Falha outbox id={row.id}: {exc}")
        if pending:
            db.commit()
        return count
    finally:
        db.close()


def run_poll_loop(interval_seconds: float = 5.0) -> None:
    """
    Loop contínuo de poll do outbox.

    Args:
        interval_seconds: Intervalo entre ciclos.

    Returns:
        None
    """
    logger.info(f"[worker] Poll mode — intervalo {interval_seconds}s")
    while True:
        processed = run_poll_once()
        if processed:
            logger.info(f"[worker] Poll processou {processed} evento(s)")
        time.sleep(interval_seconds)


def run_rabbitmq_consume_once() -> bool:
    """
    Consome uma mensagem da fila RabbitMQ.

    Returns:
        True se consumiu mensagem.
    """
    from app.shared.events.rabbitmq_adapter import get_rabbitmq_adapter

    adapter = get_rabbitmq_adapter()
    try:
        return adapter.consume_one(_handle_event)
    finally:
        adapter.close()


def run_rabbitmq_loop(interval_seconds: float = 1.0) -> None:
    """
    Loop contínuo de consumo RabbitMQ.

    Args:
        interval_seconds: Sleep quando fila vazia.

    Returns:
        None
    """
    logger.info(f"[worker] RabbitMQ mode — {settings.RABBITMQ_URL}")
    while True:
        try:
            consumed = run_rabbitmq_consume_once()
            if not consumed:
                time.sleep(interval_seconds)
        except Exception as exc:
            logger.error(f"[worker] RabbitMQ erro: {exc}")
            time.sleep(interval_seconds * 2)


def run_kafka_consume_once() -> bool:
    """
    Consome uma mensagem do tópico Kafka.

    Returns:
        True se consumiu mensagem.
    """
    from app.shared.events.kafka_adapter import get_kafka_adapter

    adapter = get_kafka_adapter()
    try:
        return adapter.consume_one(_handle_event)
    finally:
        adapter.close()


def run_kafka_loop(interval_seconds: float = 1.0) -> None:
    """
    Loop contínuo de consumo Kafka.

    Args:
        interval_seconds: Sleep quando tópico vazio.

    Returns:
        None
    """
    logger.info(f"[worker] Kafka mode — {settings.KAFKA_BOOTSTRAP_SERVERS}/{settings.KAFKA_TOPIC}")
    while True:
        try:
            consumed = run_kafka_consume_once()
            if not consumed:
                time.sleep(interval_seconds)
        except Exception as exc:
            logger.error(f"[worker] Kafka erro: {exc}")
            time.sleep(interval_seconds * 2)


def main() -> None:
    """
    CLI entrypoint do worker outbox.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="CoreFlow Outbox Worker (CF-13/14)")
    parser.add_argument(
        "--mode",
        choices=["poll", "rabbitmq", "kafka", "once"],
        default="poll",
        help="Modo: poll DB, consume RabbitMQ/Kafka ou once",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Intervalo entre ciclos (poll/rabbitmq)",
    )
    args = parser.parse_args()

    if args.mode == "once":
        count = run_poll_once()
        print(f"✅ Outbox worker (once): {count} evento(s) processado(s)")
        return

    if args.mode == "rabbitmq":
        run_rabbitmq_loop(args.interval)
        return

    if args.mode == "kafka":
        run_kafka_loop(args.interval)
        return

    if args.interval <= 0:
        count = run_poll_once()
        print(f"✅ Outbox worker (poll): {count} evento(s) processado(s)")
        return

    run_poll_loop(args.interval)


if __name__ == "__main__":
    main()
