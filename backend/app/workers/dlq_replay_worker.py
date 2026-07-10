"""
DLQ Replay Worker — replay automático com backoff (CF-20).
"""
import argparse
import time

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.shared.events.dlq_handler_replay import DlqHandlerReplayService

logger = get_logger("dlq_replay_worker")


def run_once(limit: int | None = None, force: bool = False) -> dict:
    """
    Executa um batch de replay DLQ.

    Args:
        limit: Máximo de mensagens (default settings).
        force: Ignorar backoff.

    Returns:
        Resumo do batch replay.
    """
    db = SessionLocal()
    try:
        batch_limit = limit or settings.KAFKA_DLQ_REPLAY_BATCH_SIZE
        return DlqHandlerReplayService(db).replay_batch(limit=batch_limit, force=force)
    finally:
        db.close()


def run_loop(interval_seconds: float = 60.0) -> None:
    """
    Loop contínuo de replay DLQ com intervalo fixo.

    Args:
        interval_seconds: Segundos entre batches.

    Returns:
        None
    """
    logger.info(f"[dlq-replay-worker] Loop — intervalo {interval_seconds}s")
    while True:
        try:
            result = run_once()
            if result.get("processed", 0):
                logger.info(f"[dlq-replay-worker] Batch: {result.get('counts')}")
        except Exception as exc:
            logger.error(f"[dlq-replay-worker] Erro: {exc}")
        time.sleep(interval_seconds)


def main() -> None:
    """
    CLI entrypoint do worker DLQ replay.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="CoreFlow DLQ Replay Worker (CF-20)")
    parser.add_argument(
        "--mode",
        choices=["once", "loop"],
        default="once",
        help="Executar uma vez ou loop contínuo",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limite por batch")
    parser.add_argument("--force", action="store_true", help="Ignorar backoff")
    parser.add_argument("--interval", type=float, default=60.0, help="Intervalo loop (s)")
    args = parser.parse_args()

    if args.mode == "loop":
        run_loop(args.interval)
        return

    result = run_once(limit=args.limit, force=args.force)
    print(f"✅ DLQ replay: {result}")


if __name__ == "__main__":
    main()
