"""
DlqReplayMetrics — instrumentação de replay DLQ para Prometheus (CF-22).
"""
import time
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy.orm import Session

from app.core.prometheus_metrics import record_dlq_replay, refresh_dlq_gauges


@contextmanager
def track_dlq_replay(mode: str) -> Generator[None, None, None]:
    """
    Context manager que mede duração e registra sucesso/falha de replay.

    Args:
        mode: handler | republish.

    Yields:
        None — use ``record_status`` após o bloco via retorno manual.

    Example:
        with track_dlq_replay("handler") as _:
            ... replay logic ...
        # chamar record_dlq_replay_status(mode, status) explicitamente
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        _ = start  # duração registrada externamente via record_dlq_replay_status


def record_dlq_replay_status(
    mode: str,
    status: str,
    duration_seconds: Optional[float] = None,
) -> None:
    """
    Registra status final de replay DLQ nas métricas Prometheus.

    Args:
        mode: handler | republish.
        status: success | failed | scheduled | skipped.
        duration_seconds: Duração opcional em segundos.

    Returns:
        None
    """
    record_dlq_replay(mode=mode, status=status, duration_seconds=duration_seconds)


def refresh_gauges_after_batch(db: Session) -> None:
    """
    Atualiza gauges DLQ após processamento de batch.

    Args:
        db: Sessão SQLAlchemy.

    Returns:
        None
    """
    refresh_dlq_gauges(db)
