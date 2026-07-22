"""R4-F11 — Reagendamento core-only (ADR-026).

Cobertura:
- APP_VERSION == 2.14.0-r4-f11.
- Aggregate: approved → rescheduled; pending falha.
- Handler fecha antigo + cria novo; transfere deposit_paid.
- POST /v1/bookings/{id}/reschedule (admin).
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models.agendamento import ReservationStatus
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    MoneySnapshot,
    TimeSlot,
)
from app.services.payment_reservation_service import PaymentReservationService
from app.shared.events.outbox import CoreEventOutbox


def test_app_version_r4_f11():
    """APP_VERSION avançou de R4-F11 (pin exato relaxado em R4-F12+; ver test_app_version_r4_f12)."""
    assert settings.APP_VERSION.startswith("2.")


def test_booking_reschedule_invalid_state():
    """Só approved pode ir para rescheduled."""
    booking = Booking(
        company_id=1,
        customer_id=1,
        catalog_id=1,
        offering_id=1,
        time_slot=TimeSlot(
            starts_at=datetime.now() + timedelta(days=2),
            ends_at=datetime.now() + timedelta(days=2, hours=1),
        ),
        pricing=MoneySnapshot(
            price_total=Decimal("100"),
            deposit_pct=Decimal("0.3"),
            deposit_amount=Decimal("30"),
            remaining_amount=Decimal("70"),
        ),
        status=BookingLifecycleStatus.PENDING,
    )
    with pytest.raises(InvalidBookingStateTransitionError):
        booking.reschedule("novo horario")


def test_booking_reschedule_from_approved():
    """approved → rescheduled."""
    booking = Booking(
        company_id=1,
        customer_id=1,
        catalog_id=1,
        offering_id=1,
        time_slot=TimeSlot(
            starts_at=datetime.now() + timedelta(days=2),
            ends_at=datetime.now() + timedelta(days=2, hours=1),
        ),
        pricing=MoneySnapshot(
            price_total=Decimal("100"),
            deposit_pct=Decimal("0.3"),
            deposit_amount=Decimal("30"),
            remaining_amount=Decimal("70"),
        ),
        status=BookingLifecycleStatus.APPROVED,
    )
    booking.reschedule("cliente pediu")
    assert booking.status == BookingLifecycleStatus.RESCHEDULED


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


def _create_approved_booking(
    client, db, synced_catalog, cliente_exemplo, booking_headers, admin_headers, days_ahead
):
    """
    Cria booking, confirma sinal e aprova.

    Returns:
        Dict JSON do booking approved.
    """
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead)
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
    booking = create.json()
    PaymentReservationService(db).confirmar_deposito_por_booking(booking["id"])
    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text
    return approve.json()


def test_reschedule_api_fecha_antigo_e_cria_novo(
    client,
    admin_headers,
    synced_catalog,
    cliente_exemplo,
    db,
    booking_headers,
    enable_booking_core,
):
    """POST /v1/bookings/{id}/reschedule fecha antigo e cria substituto approved."""
    catalog, offering = synced_catalog
    old = _create_approved_booking(
        client,
        db,
        synced_catalog,
        cliente_exemplo,
        booking_headers,
        admin_headers,
        days_ahead=100,
    )
    new_slot = _slot_for_day(db, catalog, offering, days_ahead=101)

    response = client.post(
        f"/v1/bookings/{old['id']}/reschedule",
        json={"scheduled_at": new_slot.isoformat(), "notes": "cliente pediu troca"},
        headers={**admin_headers, "X-Correlation-Id": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["previous_booking_id"] == old["id"]
    assert body["previous_status"] == "rescheduled"
    assert body["booking"]["id"] != old["id"]
    assert body["booking"]["status"] in ("approved", "APPROVED")
    assert body["booking"]["deposit_paid"] is True
    assert body["booking"]["customer_id"] == old["customer_id"]

    prev = db.query(CoreBooking).filter(CoreBooking.id == old["id"]).first()
    assert prev is not None
    assert prev.status == ReservationStatus.RESCHEDULED

    evt = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.event_type == "booking.rescheduled")
        .order_by(CoreEventOutbox.id.desc())
        .first()
    )
    assert evt is not None


def test_reschedule_recusa_pending(
    client,
    admin_headers,
    synced_catalog,
    cliente_exemplo,
    db,
    booking_headers,
    enable_booking_core,
):
    """Booking pending não pode ser reagendado."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=102)
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
    assert create.status_code == 201
    booking_id = create.json()["id"]
    new_slot = _slot_for_day(db, catalog, offering, days_ahead=103)
    response = client.post(
        f"/v1/bookings/{booking_id}/reschedule",
        json={"scheduled_at": new_slot.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 409, response.text
