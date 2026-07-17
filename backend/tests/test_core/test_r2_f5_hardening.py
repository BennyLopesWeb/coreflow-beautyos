"""R2-F5 — OTEL span, reconciliation drift, fitness gates."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.architecture_metrics import ArchitectureMetricsStore, identified_couplings
from app.core.telemetry import booking_create_core_span, get_tracer
from app.models.agendamento import Agendamento, ReservationStatus
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


def test_reconciliation_detects_orphan_legacy(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    FF-OBS-002: drift quando legacy_agendamento_id aponta para inexistente.

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
        legacy_agendamento_id=999999,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()

    ArchitectureMetricsStore.reset()
    count = run_once(db)
    assert count >= 1
    assert ArchitectureMetricsStore.get().get_booking_drift_count() >= 1
    db.refresh(row)
    assert row.sync_status == SyncStatus.DRIFT.value


def test_reconciliation_zero_drift_when_synced(
    db, default_company, cliente_exemplo, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """
    Reconciliação retorna 0 quando core e legado batem.

    Args:
        db: Sessão.
        default_company: Tenant.
        cliente_exemplo: Cliente.
        synced_catalog: Catalog.
        tranca_exemplo: Tranca.
        service_image_exemplo: Modelo.
    """
    catalog, offering = synced_catalog
    ag = Agendamento(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=datetime.utcnow() + timedelta(days=3),
        status=ReservationStatus.PENDING_PAYMENT,
        valor_total=Decimal("150.00"),
        valor_sinal=Decimal("45.00"),
        valor_restante=Decimal("105.00"),
    )
    db.add(ag)
    db.flush()
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=ag.data_hora,
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("150.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("45.00"),
        remaining_amount=Decimal("105.00"),
        legacy_agendamento_id=ag.id,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()

    # Isola: só este booking com legacy válido — outros fixtures podem existir
    count, ids = detect_drift(db)
    assert row.id not in ids or count == 0 or row.sync_status == SyncStatus.SYNCED.value
    db.refresh(row)
    assert row.sync_status != SyncStatus.DRIFT.value or row.legacy_agendamento_id == ag.id
    # O booking sincronizado não deve estar em drift
    assert row.id not in ids
