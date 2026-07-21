"""R2-F2 — approve/reject domain path + paridade P03–P05, P08."""
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.modules.booking.application.commands.approve_booking import (
    ApproveBookingCommand,
    ApproveBookingHandler,
)
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    MoneySnapshot,
    TimeSlot,
)
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus
from decimal import Decimal


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro slot disponível para testes de paridade.

    Args:
        db: Sessão SQLAlchemy.
        catalog: Catálogo sync.
        offering: Offering sync.
        days_ahead: Dias à frente para buscar horários.

    Returns:
        datetime do slot disponível.
    """
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _create_booking(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead: int):
    """
    Cria booking via POST /v1/bookings sem confirmar sinal.

    Args:
        client: TestClient FastAPI.
        db: Sessão de teste.
        synced_catalog: Fixture catálogo.
        cliente_exemplo: Fixture cliente.
        booking_headers: Factory de headers Idempotency-Key.
        days_ahead: Offset de dias para slot.

    Returns:
        dict JSON do booking criado.
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
    return create.json()


def test_booking_approve_invalid_state():
    """Unit — approve em approved levanta InvalidBookingStateTransitionError."""
    start = datetime.now() + timedelta(days=1)
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
    with pytest.raises(InvalidBookingStateTransitionError):
        booking.approve()


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled e booking.legacy.projection.enabled (dual-write R4-F2)."""
    both_flags = lambda key: key in (
        "booking.core.enabled",
        "booking.legacy.projection.enabled",
    )
    monkeypatch.setattr(
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        both_flags,
    )
    monkeypatch.setattr(
        "app.modules.booking.application.commands.reject_booking.feature_flags.is_enabled",
        both_flags,
    )
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        both_flags,
    )


def _create_booking_with_deposit(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=14):
    """Helper — create + confirm deposit."""
    from app.services.payment_reservation_service import PaymentReservationService

    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead
    )
    PaymentReservationService(db).confirmar_deposito(
        booking["legacy_agendamento_id"], transaction_id="tx-f2"
    )
    return booking


def test_p03_approve_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P03 — approve com sinal pago flag ON."""
    booking = _create_booking_with_deposit(
        client, db, synced_catalog, cliente_exemplo, booking_headers
    )
    corr = str(uuid.uuid4())
    response = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers={**admin_headers, "X-Correlation-Id": corr},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] in ("approved", "APPROVED")

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.approved",
            CoreEventOutbox.aggregate_id == str(booking["id"]),
        )
        .first()
    )
    assert evt is not None
    assert evt.status == OutboxStatus.PROCESSED
    payload = json.loads(evt.payload)
    assert payload.get("correlation_id") == corr


def test_p04_approve_without_deposit_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P04 — approve sem sinal retorna 409 deposit_required."""
    booking_id = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=15
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/approve",
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert "deposit_required" in response.text


def test_p05_reject_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P05 — reject pending flag ON."""
    booking_id = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=16
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/reject",
        headers=admin_headers,
        json={"reason": "Cliente desistiu"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("rejected", "REJECTED")

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.rejected",
            CoreEventOutbox.aggregate_id == str(booking_id),
        )
        .first()
    )
    assert evt is not None


def test_get_booking_etag_header(client, synced_catalog, cliente_exemplo, db, booking_headers):
    """GET booking retorna ETag W/\"{version}\"."""
    booking_id = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=17
    )["id"]
    response = client.get(f"/v1/bookings/{booking_id}")
    assert response.status_code == 200
    assert "etag" in response.headers
    assert response.headers["etag"].startswith('W/"')


def test_p04_approve_without_deposit_legacy_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P04 — approve sem sinal flag OFF (legacy ACL)."""
    booking_id = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=18
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/approve",
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert "deposit_required" in response.text or "Sinal" in response.text


def test_p05_reject_legacy_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P05 — reject pending flag OFF (legacy ACL)."""
    booking_id = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=19
    )["id"]

    response = client.post(
        f"/v1/bookings/{booking_id}/reject",
        headers=admin_headers,
        json={"reason": "Sem disponibilidade"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] in ("rejected", "REJECTED")


def test_p08_deposit_confirmed_enables_approve_core_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Paridade P08 — confirmar sinal habilita approve (flag ON)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=20
    )
    legacy_id = booking["legacy_agendamento_id"]

    blocked = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert blocked.status_code == 409

    deposit = client.post(
        "/payments/deposit/admin",
        json={"agendamento_id": legacy_id, "transaction_id": "tx-p08"},
        headers=admin_headers,
    )
    assert deposit.status_code == 200, deposit.text

    evt = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.event_type == "payment.deposit.confirmed")
        .order_by(CoreEventOutbox.id.desc())
        .first()
    )
    assert evt is not None

    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] in ("approved", "APPROVED")


def test_p08_deposit_confirmed_enables_approve_core_only_path(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P08 — confirmar sinal habilita approve (flag default OFF — R4-F2 core-only)."""
    from app.services.payment_reservation_service import PaymentReservationService

    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=21
    )
    assert booking["legacy_agendamento_id"] is None

    PaymentReservationService(db).confirmar_deposito_por_booking(booking["id"])

    approve = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] in ("approved", "APPROVED")


def test_if_match_version_conflict(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """If-Match desatualizado retorna 409 version_conflict."""
    booking = _create_booking_with_deposit(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=22
    )

    response = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers={**admin_headers, "If-Match": 'W/"999"'},
    )
    assert response.status_code == 409
    assert "version_conflict" in response.text


def test_if_match_invalid_precondition(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """If-Match malformado retorna 412 precondition_failed."""
    booking = _create_booking_with_deposit(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=23
    )

    response = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers={**admin_headers, "If-Match": "not-a-version"},
    )
    assert response.status_code == 412
    assert "precondition_failed" in response.text


def test_defer_commit_rollback_on_approve_projection_failure(
    db, synced_catalog, cliente_exemplo, default_company, monkeypatch, enable_booking_core, booking_headers, client
):
    """Integration — falha projeção approve faz rollback (status pending, sem outbox processed)."""
    booking = _create_booking_with_deposit(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=24
    )
    booking_id = booking["id"]

    handler = ApproveBookingHandler(db)
    monkeypatch.setattr(
        handler.booking_port,
        "project_approve_booking",
        MagicMock(side_effect=RuntimeError("projection failed")),
    )

    with pytest.raises(RuntimeError):
        handler.execute(
            ApproveBookingCommand(
                booking_id=booking_id,
                company_id=default_company.id,
            )
        )

    row = db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
    assert row.status.value in ("pending_payment", "PENDING_PAYMENT", "pendente")

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.approved",
            CoreEventOutbox.aggregate_id == str(booking_id),
            CoreEventOutbox.status == OutboxStatus.PROCESSED,
        )
        .first()
    )
    assert evt is None
