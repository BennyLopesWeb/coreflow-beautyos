"""
R4-F3 — Dual-write outbound (project_*) removido definitivamente (ADR-024 sunset / RFC-003 M7).

Sucede ``test_r4_f2_dual_write_off.py`` (R4-F2 apenas desligava o dual-write
por padrão via feature flag, mantendo o código para rollback). Prova que:

- A feature flag ``FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED`` /
  ``booking.legacy.projection.enabled`` não existe mais — não há kill-switch
  porque não há mais código de dual-write para reativar.
- ``LegacyBookingAdapter`` não expõe mais nenhum método ``project_*``.
- create/approve/reject/cancel continuam funcionando 100% core-only, sem
  ``legacy_agendamento_id`` nem linha em ``agendamentos``.
- Reconciliation não trata booking core-only como drift.
- APP_VERSION == 2.6.0-r4-f3.
"""
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.core.feature_flags import feature_flags
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.workers.booking_reconciliation_worker import detect_drift


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro horário disponível N dias à frente.

    Args:
        db: Sessão SQLAlchemy de teste.
        catalog: Fixture CoreCatalog sincronizado.
        offering: Fixture CoreOffering sincronizado.
        days_ahead: Deslocamento em dias para o slot candidato.

    Returns:
        datetime do primeiro horário disponível encontrado.
    """
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _create_booking(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead: int) -> dict:
    """
    Cria booking via ``POST /v1/bookings`` — sempre core-only (R4-F3).

    Args:
        client: TestClient FastAPI.
        db: Sessão SQLAlchemy de teste.
        synced_catalog: Tupla (CoreCatalog, CoreOffering) sincronizados.
        cliente_exemplo: Fixture de cliente legado.
        booking_headers: Factory de headers Idempotency-Key.
        days_ahead: Deslocamento em dias para o slot.

    Returns:
        Dict JSON do booking criado (resposta 201).
    """
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead)
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_app_version_r4_f3():
    """APP_VERSION avançou de R4-F3 (pin exato relaxado em R4-F4+; ver test_app_version_r4_f4)."""
    assert settings.APP_VERSION.startswith("2.")


def test_legacy_projection_flag_removed():
    """R4-F3 — a flag de dual-write outbound foi removida definitivamente."""
    assert not hasattr(settings, "FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED")
    with pytest.raises(KeyError):
        feature_flags.is_enabled("booking.legacy.projection.enabled")


def test_legacy_booking_adapter_has_no_project_methods():
    """R4-F3 — LegacyBookingAdapter não expõe mais nenhum método project_*."""
    for name in (
        "project_create_booking",
        "project_approve_booking",
        "project_reject_booking",
        "project_cancel_booking",
    ):
        assert not hasattr(LegacyBookingAdapter, name), f"{name} deveria ter sido removido em R4-F3"


def test_create_booking_default_no_legacy_projection(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Create não gera legacy_agendamento_id nem Agendamento (sem dual-write)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=50
    )

    assert booking["legacy_agendamento_id"] is None
    assert booking["status"] == "pending_payment"

    row = db.query(CoreBooking).filter(CoreBooking.id == booking["id"]).first()
    assert row is not None
    assert row.legacy_agendamento_id is None
    assert row.sync_status == SyncStatus.SYNCED.value


def test_approve_core_only_booking_without_legacy(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Approve funciona core-only via confirmar_deposito_por_booking (sem Agendamento)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=51
    )
    assert booking["legacy_agendamento_id"] is None

    blocked = client.post(f"/v1/bookings/{booking['id']}/approve", headers=admin_headers)
    assert blocked.status_code == 409
    assert "deposit_required" in blocked.text

    PaymentReservationService(db).confirmar_deposito_por_booking(booking["id"])

    approve = client.post(f"/v1/bookings/{booking['id']}/approve", headers=admin_headers)
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] in ("approved", "APPROVED")

    row = db.query(CoreBooking).filter(CoreBooking.id == booking["id"]).first()
    assert row.legacy_agendamento_id is None
    assert row.deposit_paid is True


def test_reject_core_only_booking_without_legacy(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Reject funciona sem legacy_agendamento_id e sem levantar ValidationError."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=52
    )
    assert booking["legacy_agendamento_id"] is None

    response = client.post(
        f"/v1/bookings/{booking['id']}/reject",
        headers=admin_headers,
        json={"reason": "Sem disponibilidade"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("rejected", "REJECTED")


def test_cancel_core_only_booking_without_legacy(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Cancel funciona sem legacy_agendamento_id e sem levantar ValidationError."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=53
    )
    assert booking["legacy_agendamento_id"] is None

    response = client.post(
        f"/v1/bookings/{booking['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Cliente desistiu"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("cancelled", "CANCELLED")


def test_reconciliation_core_only_booking_not_drift(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Reconciliation não marca booking sem legacy_agendamento_id como drift."""
    from decimal import Decimal

    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=54),
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()

    count, ids = detect_drift(db)
    assert row.id not in ids
    db.refresh(row)
    assert row.sync_status != SyncStatus.DRIFT.value


def test_reconciliation_nao_mais_flags_orphan_legacy_reference(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    Reconciliation não detecta mais drift por ``legacy_agendamento_id``
    órfão (R4-F8 — tabela ``agendamentos`` removida via DROP físico,
    ADR-024 sunset / RFC-003 M11+; não há mais projeção legado para
    comparar contra ``core_bookings``). Cobre bookings históricos criados
    antes de R4-F3 (quando o dual-write ainda existia) que possam ter
    ficado com referência legado órfã — o inteiro histórico é preservado,
    mas não bloqueia/marca mais nada.
    """
    from decimal import Decimal

    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=55),
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=888888,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()

    count, ids = detect_drift(db)
    assert row.id not in ids
    assert count == 0
    db.refresh(row)
    assert row.sync_status == SyncStatus.SYNCED.value


def test_queue_aprovar_com_horario_sem_agendamento_id(
    db, synced_catalog, cliente_exemplo
):
    """QueueEntryService.aprovar_com_horario não levanta erro sem dual-write (R4-F3)."""
    from app.models.queue_entry import QueueEntry, QueueEntryStatus
    from app.services.queue_entry_service import QueueEntryService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=57),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    entry = QueueEntry(
        company_id=1,
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        posicao=1,
        data=slot.horario.date(),
        horario_entrada=datetime.now().time(),
        status=QueueEntryStatus.WAITING,
        observacoes="fila r4-f3",
        mesmo_dia=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    updated = QueueEntryService(db).aprovar_com_horario(entry.id, slot.horario)
    assert updated.agendamento_id is None
    assert updated.status == QueueEntryStatus.WAITING
