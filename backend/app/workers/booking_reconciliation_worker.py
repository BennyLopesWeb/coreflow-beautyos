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
from app.models.agendamento import Agendamento, ReservationStatus
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    SyncStatus,
)

logger = get_logger("booking_reconciliation")

_ORM_TO_LIFECYCLE = {
    ReservationStatus.PENDING_PAYMENT: BookingLifecycleStatus.PENDING,
    ReservationStatus.PENDING_APPROVAL: BookingLifecycleStatus.PENDING,
    ReservationStatus.WAITING_TIME_CONFIRMATION: BookingLifecycleStatus.PENDING,
    ReservationStatus.APPROVED: BookingLifecycleStatus.APPROVED,
    ReservationStatus.REJECTED: BookingLifecycleStatus.REJECTED,
    ReservationStatus.CANCELLED: BookingLifecycleStatus.CANCELLED,
    ReservationStatus.PENDENTE: BookingLifecycleStatus.PENDING,
    ReservationStatus.CONFIRMADO: BookingLifecycleStatus.APPROVED,
}


def _lifecycle_from_orm(status) -> BookingLifecycleStatus:
    """
    Mapeia status ORM legado → lifecycle canônico.

    Args:
        status: Enum ou string ReservationStatus.

    Returns:
        BookingLifecycleStatus.
    """
    if hasattr(status, "value"):
        key = ReservationStatus(status.value) if isinstance(status.value, str) else status
    else:
        key = ReservationStatus(status)
    return _ORM_TO_LIFECYCLE.get(key, BookingLifecycleStatus.PENDING)


def _core_lifecycle(status) -> BookingLifecycleStatus:
    """
    Normaliza status do core_bookings para lifecycle.

    Args:
        status: Valor ORM core.

    Returns:
        BookingLifecycleStatus.
    """
    return _lifecycle_from_orm(status)


def detect_drift(db: Session) -> Tuple[int, List[int]]:
    """
    Compara ``core_bookings`` com ``agendamentos`` e marca sync_status=drift.

    Regras (ADR-024 / R4-F2 sunset):
    - ``legacy_agendamento_id is None`` → **não é drift**. Com
      ``booking.legacy.projection.enabled`` OFF (default), bookings
      core-only nunca tiveram projeção legado — não há nada para
      reconciliar, então ``SYNCED`` é o estado correto.
    - ``legacy_agendamento_id`` presente mas ``Agendamento`` órfão
      (inexistente) → drift.
    - ``legacy_agendamento_id`` presente e status canônico divergente → drift.

    Args:
        db: Sessão SQLAlchemy.

    Returns:
        Tupla (drift_count, lista de booking ids em drift).
    """
    rows = (
        db.query(CoreBooking)
        .filter(CoreBooking.deleted_at.is_(None))
        .all()
    )
    drifted: List[int] = []
    for row in rows:
        is_drift = False
        if row.legacy_agendamento_id:
            legacy = (
                db.query(Agendamento)
                .filter(Agendamento.id == row.legacy_agendamento_id)
                .first()
            )
            if legacy is None:
                is_drift = True
            else:
                core_lc = _core_lifecycle(row.status)
                legacy_lc = _lifecycle_from_orm(legacy.status)
                if core_lc != legacy_lc:
                    is_drift = True

        if is_drift:
            drifted.append(row.id)
            row.sync_status = SyncStatus.DRIFT.value
        elif row.sync_status == SyncStatus.DRIFT.value:
            row.sync_status = SyncStatus.SYNCED.value

    if drifted:
        db.commit()
    return len(drifted), drifted


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
