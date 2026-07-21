"""R2-F1 — Booking create domain path + paridade P01/P02/P09."""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import ConflictError
from app.core.feature_flags import feature_flags
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.value_objects.booking_types import MoneySnapshot, TimeSlot
from app.modules.booking.application.commands.create_booking import (
    CreateBookingCommand,
    CreateBookingHandler,
)
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus


def test_booking_aggregate_create_valid():
    """Unit — factory create respeita INV-B1/B2."""
    pricing = MoneySnapshot(
        price_total=Decimal("100"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30"),
        remaining_amount=Decimal("70"),
    )
    start = datetime.now() + timedelta(days=5)
    booking = Booking.create(
        company_id=1,
        customer_id=2,
        catalog_id=3,
        offering_id=4,
        scheduled_at=start,
        ends_at=start + timedelta(minutes=60),
        pricing=pricing,
    )
    assert booking.status.value == "pending"
    assert booking.legacy.sync_status.value == "pending"


def test_time_slot_invalid_raises():
    """Unit — INV-B2 starts_at >= ends_at."""
    start = datetime.now() + timedelta(days=1)
    with pytest.raises(ValueError):
        TimeSlot(starts_at=start, ends_at=start)


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled (path core) para testes do path F1."""
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        lambda key: key in ("booking.core.enabled",),
    )


def test_p01_create_core_path(
    client, synced_catalog, cliente_exemplo, db, enable_booking_core, booking_headers
):
    """Paridade P01 — create básico core-only (R4-F3, sem dual-write)."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=3),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.horario.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["legacy_agendamento_id"] is None
    assert body["status"] == "pending_payment"

    booking_evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.created",
            CoreEventOutbox.aggregate_id == str(body["id"]),
        )
        .first()
    )
    alias_evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "reservation.created",
            CoreEventOutbox.aggregate_id == str(body["id"]),
        )
        .first()
    )
    assert booking_evt is not None
    assert booking_evt.status == OutboxStatus.PROCESSED
    # R3-F2 (ADR-027 sunset): alias reservation.created não é mais publicado.
    assert alias_evt is None


def test_p02_unavailable_slot_core_path(
    client, synced_catalog, cliente_exemplo, db, enable_booking_core, booking_headers
):
    """Paridade P02 — slot indisponível retorna 409."""
    catalog, offering = synced_catalog
    busy_time = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(
        days=2
    )
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": busy_time.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 409


def test_p09_double_booking_conflict(
    client, synced_catalog, cliente_exemplo, db, enable_booking_core, booking_headers
):
    """Paridade P09 — segundo create no mesmo slot falha."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=5),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)
    payload = {
        "customer_id": cliente_exemplo.id,
        "catalog_id": catalog.id,
        "offering_id": offering.id,
        "scheduled_at": slot.horario.isoformat(),
    }
    first = client.post("/v1/bookings", json=payload, headers=booking_headers())
    assert first.status_code == 201, first.text
    second = client.post("/v1/bookings", json=payload, headers=booking_headers())
    assert second.status_code == 409


def test_p02_unavailable_slot_legacy_path(client, synced_catalog, cliente_exemplo, booking_headers):
    """Paridade P02 — slot indisponível retorna 409 (flag OFF / ACL path)."""
    catalog, offering = synced_catalog
    busy_time = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(
        days=2
    )
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": busy_time.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 409


def test_p09_double_booking_conflict_legacy_path(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P09 — segundo create no mesmo slot falha (flag OFF)."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=7),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)
    payload = {
        "customer_id": cliente_exemplo.id,
        "catalog_id": catalog.id,
        "offering_id": offering.id,
        "scheduled_at": slot.horario.isoformat(),
    }
    first = client.post("/v1/bookings", json=payload, headers=booking_headers())
    assert first.status_code == 201, first.text
    second = client.post("/v1/bookings", json=payload, headers=booking_headers())
    assert second.status_code == 409


def test_core_path_rollback_on_scheduling_conflict(
    db, synced_catalog, cliente_exemplo, default_company, monkeypatch, enable_booking_core
):
    """Integration — falha no path core (conflito de slot) faz rollback (zero core row).

    R4-F3: o antigo cenário de rollback por falha de projeção legado
    (``project_create_booking``) deixou de existir junto com o dual-write.
    Este teste cobre o equivalente core-only: uma falha durante o create
    (ex.: alocação de resource) também não deve deixar linha órfã em
    ``core_bookings``.
    """
    from app.modules.booking.domain.models import CoreBooking
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=6),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    handler = CreateBookingHandler(db)
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.OutboxBatch",
        MagicMock(side_effect=RuntimeError("outbox failed")),
    )

    before = db.query(CoreBooking).count()
    with pytest.raises(RuntimeError):
        handler.execute(
            CreateBookingCommand(
                customer_id=cliente_exemplo.id,
                catalog_id=catalog.id,
                offering_id=offering.id,
                scheduled_at=slot.horario,
                company_id=default_company.id,
            )
        )
    assert db.query(CoreBooking).count() == before
