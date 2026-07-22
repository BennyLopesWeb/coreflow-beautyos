"""
Booking reconciliation worker — detecta drift core↔legado (ADR-024 / R2-F5).

Job periódico recomendado: a cada 5 min, timeout 60s.
"""
from __future__ import annotations

import argparse
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.logging_config import get_logger
from app.core.prometheus_metrics import set_booking_drift_count
from app.db.session import SessionLocal
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus

logger = get_logger("booking_reconciliation")


def detect_drift(db: Session) -> Tuple[int, List[int]]:
    """
    Compara ``core_bookings`` com a projeção legado e marca sync_status=drift.

    .. deprecated:: 2.11.0-r4-f8
        A tabela ``agendamentos`` foi removida (DROP físico — ADR-024
        sunset / RFC-003 M11+) — a comparação com ``Agendamento`` legado
        (órfão ou status divergente) foi retirada. Desde R4-F3, o
        dual-write outbound já havia sido removido do código (todo
        booking novo é core-only, ``legacy_agendamento_id is None``);
        agora, com a tabela removida, não há mais nenhuma projeção legado
        para reconciliar contra — este método sempre reporta ``0`` drift
        e normaliza qualquer ``sync_status=DRIFT`` residual para
        ``SYNCED`` (o conceito de sync legado está retirado nesta
        release).

    Args:
        db: Sessão SQLAlchemy.

    Returns:
        Tupla ``(0, [])`` — sempre sem drift.
    """
    rows = (
        db.query(CoreBooking)
        .filter(
            CoreBooking.deleted_at.is_(None),
            CoreBooking.sync_status == SyncStatus.DRIFT.value,
        )
        .all()
    )
    for row in rows:
        row.sync_status = SyncStatus.SYNCED.value

    if rows:
        db.commit()
    return 0, []


def run_once(db: Optional[Session] = None) -> int:
    """
    Executa uma passagem de reconciliação e atualiza métricas.

    Args:
        db: Sessão opcional (cria SessionLocal se None).

    Returns:
        drift_count atual.
    """
    owns = db is None
    session = db or SessionLocal()
    try:
        count, ids = detect_drift(session)
        ArchitectureMetricsStore.get().record_booking_drift_count(count)
        set_booking_drift_count(count)
        logger.info(
            "[reconciliation] drift_count=%s ids=%s",
            count,
            ids[:20],
        )
        return count
    finally:
        if owns:
            session.close()


def main() -> None:
    """
    CLI — ``python -m app.workers.booking_reconciliation_worker --once``.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Booking reconciliation (ADR-024)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma passagem e encerra",
    )
    args = parser.parse_args()
    if args.once:
        run_once()
        return
    # Default: uma passagem (cron externo cuida do intervalo 5 min)
    run_once()


if __name__ == "__main__":
    main()
