"""
R2-F5 — OTEL span, reconciliation drift, fitness gates.

.. deprecated:: 2.11.0-r4-f8
    ``detect_drift``/``run_once`` tornaram-se no-ops — a tabela
    ``agendamentos`` foi removida (DROP físico — ADR-024 sunset / RFC-003
    M11+), então não há mais projeção legado para comparar contra
    ``core_bookings``. Os testes que exercitavam a detecção de drift
    (órfão/divergente) foram reescritos para refletir o novo
    comportamento (sempre ``0`` drift; qualquer ``sync_status=DRIFT``
    residual é normalizado para ``SYNCED``).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.architecture_metrics import ArchitectureMetricsStore, identified_couplings
from app.core.telemetry import booking_create_core_span, get_tracer
from app.models.agendamento import ReservationStatus
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.workers.booking_reconciliation_worker import detect_drift, run_once


def test_ff_cpl_001_couplings_at_most_three():
    """FF-CPL-001: acoplamentos ativos ≤ 3."""
    assert len(identified_couplings()) <= 3


def test_otel_booking_create_core_span_helper():
    """FF-OBS-001: helper emite span name booking.create.core (no-op seguro)."""
    tracer = get_tracer("booking")
    assert hasattr(tracer, "start_as_current_span")
    with booking_create_core_span(company_id=1, catalog_id=2, offering_id=3) as span:
        assert span is not None
        span.set_attribute("test", "ok")


def test_reconciliation_normaliza_drift_residual_para_synced(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    FF-OBS-002 (R4-F8): sem tabela legado, detect_drift normaliza qualquer
    ``sync_status=DRIFT`` residual para ``SYNCED`` e sempre reporta 0.

    Args:
        db: Sessão.
        default_company: Tenant.
        cliente_exemplo: Cliente.
        synced_catalog: Catalog/offering.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=2),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.DRIFT.value,
        version=1,
    )
    db.add(row)
    db.commit()

    ArchitectureMetricsStore.reset()
    count = run_once(db)
    assert count == 0
    assert ArchitectureMetricsStore.get().get_booking_drift_count() == 0
    db.refresh(row)
    assert row.sync_status == SyncStatus.SYNCED.value


def test_reconciliation_zero_drift_when_synced(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    Reconciliação retorna 0 quando o booking já está SYNCED (sem tabela legado).

    Args:
        db: Sessão.
        default_company: Tenant.
        cliente_exemplo: Cliente.
        synced_catalog: Catalog.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=3),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("150.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("45.00"),
        remaining_amount=Decimal("105.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()

    count, ids = detect_drift(db)
    assert count == 0
    assert row.id not in ids
    db.refresh(row)
    assert row.sync_status == SyncStatus.SYNCED.value
