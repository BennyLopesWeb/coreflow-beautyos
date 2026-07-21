"""R2-F2b — cancel domain path + paridade P06–P07."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.modules.booking.application.commands.cancel_booking import (
    CancelBookingCommand,
    CancelBookingHandler,
)
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    MoneySnapshot,
    TimeSlot,
)
from app.modules.booking.infrastructure.adapters.cancel_policy_adapter import (
    LegacyCancelPolicyAdapter,
)
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus
from decimal import Decimal


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro slot disponível para testes.

    Args:
        db: Sessão SQLAlchemy.
        catalog: Catálogo sync.
        offering: Offering sync.
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
    """Ativa booking.core.enabled e booking.legacy.projection.enabled (dual-write R4-F2)."""
    both_flags = lambda key: key in (
        "booking.core.enabled",
        "booking.legacy.projection.enabled",
    )
    for path in (
        "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
    ):
        monkeypatch.setattr(path, both_flags)


def _create_booking_api(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead):
    """Helper create booking."""
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
    return create.json()


def test_booking_cancel_invalid_state():
    """Unit — cancel em rejected levanta InvalidBookingStateTransitionError."""
    start = datetime.now(timezone.utc) + timedelta(days=1)
    booking = Booking(
        company_id=1,
        customer_id=2,
        catalog_id=3,
        offering_id=4,
        time_slot=TimeSlot(starts_at=start, ends_at=start + timedelta(hours=1)),
        pricing=MoneySnapshot(
            price_total=Decimal("100"),
            deposit_pct=Decimal("0.3"),
            deposit_amount=Decimal("30"),
            remaining_amount=Decimal("70"),
        ),
        status=BookingLifecycleStatus.REJECTED,
        id=1,
        version=2,
    )
    with pytest.raises(InvalidBookingStateTransitionError):
        booking.cancel("motivo")


def test_cancel_policy_24h_boundary():
    """Unit — policy ≥24h inclusive no limite exato."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    booking = Booking(
        company_id=1,
        customer_id=2,
        catalog_id=3,
        offering_id=4,
        time_slot=TimeSlot(starts_at=start, ends_at=start + timedelta(hours=1)),
        pricing=MoneySnapshot(
            price_total=Decimal("100"),
            deposit_pct=Decimal("0.3"),
            deposit_amount=Decimal("30"),
            remaining_amount=Decimal("70"),
        ),
        status=BookingLifecycleStatus.APPROVED,
        id=1,
        version=2,
    )
    policy = LegacyCancelPolicyAdapter()

    class Clock24h:
        def now_utc(self):
            return datetime(2026, 7, 9, 15, 0, tzinfo=timezone.utc)

    class ClockTooLate:
        def now_utc(self):
            return datetime(2026, 7, 9, 15, 1, tzinfo=timezone.utc)

    assert policy.may_cancel(booking, Clock24h()) is True
    assert policy.may_cancel(booking, ClockTooLate()) is False


def test_p06_cancel_pending_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P06 — cancel pending flag ON."""
    booking_id = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=25
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/cancel",
        headers=admin_headers,
        json={"reason": "Cliente desistiu"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("cancelled", "CANCELLED")

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.cancelled",
            CoreEventOutbox.aggregate_id == str(booking_id),
        )
        .first()
    )
    assert evt is not None
    assert evt.status == OutboxStatus.PROCESSED


def test_p06_cancel_pending_legacy_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P06 — cancel pending flag OFF."""
    booking_id = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=26
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/cancel",
        headers=admin_headers,
        json={"reason": "Legacy cancel"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("cancelled", "CANCELLED")


def test_p07_cancel_approved_core_only_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P07 — cancel approved permissivo flag default OFF (R4-F2 core-only)."""
    from app.services.payment_reservation_service import PaymentReservationService

    booking = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=27
    )
    assert booking["legacy_agendamento_id"] is None
    PaymentReservationService(db).confirmar_deposito_por_booking(booking["id"])
    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text

    cancel = client.post(
        f"/v1/bookings/{booking['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Imprevisto"},
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] in ("cancelled", "CANCELLED")


def test_p07_cancel_approved_core_path_far_slot(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P07 — cancel approved flag ON com slot >24h."""
    from app.services.payment_reservation_service import PaymentReservationService

    booking = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=28
    )
    PaymentReservationService(db).confirmar_deposito(
        booking["legacy_agendamento_id"], transaction_id="tx-p07-core"
    )
    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text

    cancel = client.post(
        f"/v1/bookings/{booking['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Policy ok"},
    )
    assert cancel.status_code == 200, cancel.text


def test_p07_cancel_approved_within_24h_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core, monkeypatch
):
    """Paridade P07 — cancel approved <24h retorna 409 flag ON."""
    from app.services.payment_reservation_service import PaymentReservationService

    booking = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=29
    )
    PaymentReservationService(db).confirmar_deposito(
        booking["legacy_agendamento_id"], transaction_id="tx-p07-block"
    )
    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text

    monkeypatch.setattr(
        LegacyCancelPolicyAdapter,
        "may_cancel",
        lambda self, booking, clock: False,
    )

    cancel = client.post(
        f"/v1/bookings/{booking['id']}/cancel",
        headers=admin_headers,
        json={},
    )
    assert cancel.status_code == 409
    assert "cancel_policy_violation" in cancel.text


def test_defer_commit_rollback_on_cancel_projection_failure(
    db, synced_catalog, cliente_exemplo, default_company, monkeypatch, enable_booking_core, booking_headers, client
):
    """Rollback TX cancel — falha projeção não persiste outbox processed."""
    from app.modules.booking.domain.models import CoreBooking

    booking_id = _create_booking_api(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=30
    )["id"]

    handler = CancelBookingHandler(db)
    monkeypatch.setattr(
        handler.booking_port,
        "project_cancel_booking",
        MagicMock(side_effect=RuntimeError("projection failed")),
    )

    with pytest.raises(RuntimeError):
        handler.execute(
            CancelBookingCommand(
                booking_id=booking_id,
                company_id=default_company.id,
                reason="test rollback",
            )
        )

    row = db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
    assert row.status.value in ("pending_payment", "PENDING_PAYMENT", "pendente", "pending")

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.cancelled",
            CoreEventOutbox.aggregate_id == str(booking_id),
            CoreEventOutbox.status == OutboxStatus.PROCESSED,
        )
        .first()
    )
    assert evt is None
