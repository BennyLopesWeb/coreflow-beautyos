"""R4-F13 — Lifecycle ADR-026: complete / no_show / expired.

Cobertura:
- APP_VERSION == 2.16.0-r4-f13.
- Domain transitions.
- POST /v1/bookings/{id}/complete e /no-show.
- ExpireBooking via DisponibilidadeService.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    MoneySnapshot,
    SyncStatus,
    TimeSlot,
)
from app.services.payment_reservation_service import PaymentReservationService
from app.shared.events.outbox import CoreEventOutbox


from tests.helpers_ledger import seed_ledger_deposit
def test_app_version_r4_f13():
    """APP_VERSION avançou de R4-F13 (pin exato relaxado em R4-F14+)."""
    assert settings.APP_VERSION.startswith("2.")


def _booking_entity(status: BookingLifecycleStatus) -> Booking:
    """
    Cria aggregate Booking de teste.

    Args:
        status: Estado lifecycle inicial.

    Returns:
        Booking em memória.
    """
    return Booking(
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
        status=status,
    )


def test_domain_complete_no_show_expire():
    """Transições canônicas ADR-026."""
    b = _booking_entity(BookingLifecycleStatus.APPROVED)
    b.complete()
    assert b.status == BookingLifecycleStatus.COMPLETED

    b2 = _booking_entity(BookingLifecycleStatus.APPROVED)
    b2.mark_no_show("faltou")
    assert b2.status == BookingLifecycleStatus.NO_SHOW

    b3 = _booking_entity(BookingLifecycleStatus.PENDING)
    b3.expire("timeout")
    assert b3.status == BookingLifecycleStatus.EXPIRED

    with pytest.raises(InvalidBookingStateTransitionError):
        _booking_entity(BookingLifecycleStatus.PENDING).complete()


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """Retorna primeiro slot disponível."""
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled."""

    def _flag(key):
        return key in ("booking.core.enabled",)

    for path in (
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.complete_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.mark_no_show_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.expire_booking.feature_flags.is_enabled",
    ):
        monkeypatch.setattr(path, _flag)


def test_complete_and_no_show_api(
    client,
    admin_headers,
    synced_catalog,
    cliente_exemplo,
    db,
    booking_headers,
    enable_booking_core,
):
    """POST complete e no-show em bookings approved."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=120)
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
    booking_id = create.json()["id"]
    seed_ledger_deposit(db, booking_id)
    PaymentReservationService(db).confirmar_deposito_por_booking(
        booking_id, company_id=cliente_exemplo.company_id
    )
    assert (
        client.post(f"/v1/bookings/{booking_id}/approve", headers=admin_headers).status_code
        == 200
    )

    complete = client.post(
        f"/v1/bookings/{booking_id}/complete",
        json={},
        headers={**admin_headers, "X-Correlation-Id": str(uuid.uuid4())},
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["status"] in ("completed", "COMPLETED")

    evt = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.event_type == "booking.completed")
        .order_by(CoreEventOutbox.id.desc())
        .first()
    )
    assert evt is not None

    # segundo booking para no-show
    slot2 = _slot_for_day(db, catalog, offering, days_ahead=121)
    create2 = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot2.isoformat(),
        },
        headers=booking_headers(),
    )
    bid2 = create2.json()["id"]
    seed_ledger_deposit(db, bid2)
    PaymentReservationService(db).confirmar_deposito_por_booking(
        bid2, company_id=cliente_exemplo.company_id
    )
    client.post(f"/v1/bookings/{bid2}/approve", headers=admin_headers)
    ns = client.post(
        f"/v1/bookings/{bid2}/no-show",
        json={"reason": "cliente nao apareceu"},
        headers=admin_headers,
    )
    assert ns.status_code == 200, ns.text
    assert ns.json()["status"] in ("no_show", "NO_SHOW")


def test_expire_via_disponibilidade(db, default_company, cliente_exemplo, synced_catalog, enable_booking_core):
    """ExpireBooking marca pending antigo como expired."""
    from app.modules.booking.application.commands.expire_booking import (
        ExpireBookingCommand,
        ExpireBookingHandler,
    )

    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=130),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=Decimal("100"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30"),
        remaining_amount=Decimal("70"),
        deposit_paid=False,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # força created_at antigo
    row.created_at = datetime.now() - timedelta(hours=72)
    db.commit()

    ExpireBookingHandler(db).execute(
        ExpireBookingCommand(
            booking_id=row.id,
            company_id=default_company.id,
            reason="expirado",
        )
    )
    db.refresh(row)
    assert row.status == ReservationStatus.EXPIRED
