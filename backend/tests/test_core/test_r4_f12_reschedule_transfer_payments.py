"""R4-F12 — Transferência de Payment/core_payments no reagendamento.

Cobertura:
- APP_VERSION == 2.15.0-r4-f12.
- Após reschedule, linhas ``payments`` (DEPOSIT) mudam ``booking_id`` para o novo.
- ``core_payments`` sincronizados também são reatribuídos.
- Booking antigo fica sem payments ativos; novo mantém ``deposit_paid``.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.payments.application.legacy_sync_service import PaymentLegacySyncService
from app.modules.payments.domain.models import CorePayment
from app.services.payment_reservation_service import PaymentReservationService


def test_app_version_r4_f12():
    """APP_VERSION marca a release R4-F12 (transfer Payment no reschedule)."""
    assert settings.APP_VERSION == "2.15.0-r4-f12"


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro slot disponível.

    Args:
        db: Sessão.
        catalog: Catálogo.
        offering: Offering.
        days_ahead: Dias à frente.

    Returns:
        datetime do slot.
    """
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled para create/approve/reschedule."""

    def _flag(key):
        return key in ("booking.core.enabled",)

    for path in (
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.reschedule_booking.feature_flags.is_enabled",
    ):
        monkeypatch.setattr(path, _flag)


def test_reschedule_transfere_payment_e_core_payment(
    client,
    admin_headers,
    synced_catalog,
    cliente_exemplo,
    db,
    booking_headers,
    enable_booking_core,
):
    """
    Reschedule reatribui Payment DEPOSIT e CorePayment para o booking novo.

    Args (fixtures):
        client: TestClient.
        admin_headers: Auth admin.
        synced_catalog: Catálogo sync.
        cliente_exemplo: Cliente.
        db: Sessão.
        booking_headers: Headers com idempotency.
        enable_booking_core: Flag core ON.
    """
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=110)
    create = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert create.status_code == 201, create.text
    old_id = create.json()["id"]

    PaymentReservationService(db).confirmar_deposito_por_booking(old_id)
    PaymentLegacySyncService(db).sync_all()

    pag_antes = db.query(Payment).filter(Payment.booking_id == old_id).first()
    assert pag_antes is not None
    assert pag_antes.status == PaymentStatus.PAID
    assert pag_antes.tipo in (PaymentType.DEPOSIT, PaymentType.SINAL)

    core_pay_antes = (
        db.query(CorePayment).filter(CorePayment.booking_id == old_id).first()
    )
    assert core_pay_antes is not None

    approve = client.post(f"/v1/bookings/{old_id}/approve", headers=admin_headers)
    assert approve.status_code == 200, approve.text

    new_slot = _slot_for_day(db, catalog, offering, days_ahead=111)
    response = client.post(
        f"/v1/bookings/{old_id}/reschedule",
        json={"scheduled_at": new_slot.isoformat(), "notes": "troca horario"},
        headers={**admin_headers, "X-Correlation-Id": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    new_id = response.json()["booking"]["id"]
    assert new_id != old_id
    assert response.json()["booking"]["deposit_paid"] is True

    assert db.query(Payment).filter(Payment.booking_id == old_id).count() == 0
    pag_novo = db.query(Payment).filter(Payment.booking_id == new_id).first()
    assert pag_novo is not None
    assert pag_novo.id == pag_antes.id
    assert pag_novo.status == PaymentStatus.PAID

    assert db.query(CorePayment).filter(CorePayment.booking_id == old_id).count() == 0
    core_pay_novo = (
        db.query(CorePayment).filter(CorePayment.booking_id == new_id).first()
    )
    assert core_pay_novo is not None
    assert core_pay_novo.id == core_pay_antes.id

    old_row = db.query(CoreBooking).filter(CoreBooking.id == old_id).first()
    assert old_row is not None
    # Flag histórico permanece no booking fechado; SoT operacional é o novo.
    assert old_row.deposit_paid is True
