"""R2-F3 — Paridade P11 resource indisponível (flag ON + OFF)."""
from datetime import datetime, timedelta

import pytest

from app.modules.scheduling.domain.models import (
    CoreScheduleBlock,
    ScheduleBlockStatus,
)


@pytest.fixture
def enable_booking_and_resource(monkeypatch):
    """Ativa booking.core + resource.engine para path F3."""

    def _is_enabled(key: str) -> bool:
        return key in ("booking.core.enabled", "resource.engine.enabled")

    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        _is_enabled,
    )


@pytest.fixture
def enable_booking_only(monkeypatch):
    """Ativa apenas booking.core (resource engine OFF)."""
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        lambda key: key == "booking.core.enabled",
    )


def _occupy_resource(db, company_id: int, resource_id: int, location_id: int, starts_at):
    """
    Cria schedule block ocupando o resource.

    Args:
        db: Sessão.
        company_id: Tenant.
        resource_id: Resource.
        location_id: Location.
        starts_at: Início do bloco.
    """
    block = CoreScheduleBlock(
        company_id=company_id,
        resource_id=resource_id,
        location_id=location_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=60),
        status=ScheduleBlockStatus.SCHEDULED,
    )
    db.add(block)
    db.commit()


def test_p11_resource_unavailable_flag_on(
    client,
    synced_scheduling,
    cliente_exemplo,
    db,
    enable_booking_and_resource,
    booking_headers,
    default_company,
):
    """P11 — create com resource_id ocupado → 409 resource_unavailable (flag ON)."""
    catalog = synced_scheduling["catalog"]
    offering = synced_scheduling["offering"]
    resource = synced_scheduling["resource"]
    location = synced_scheduling["location"]

    starts_at = (datetime.now() + timedelta(days=5)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    _occupy_resource(db, default_company.id, resource.id, location.id, starts_at)

    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": starts_at.isoformat(),
            "resource_id": resource.id,
        },
        headers=booking_headers(),
    )
    assert response.status_code == 409, response.text
    payload = response.json()
    detail = str(payload.get("message") or payload.get("detail") or "").lower()
    assert "resource_unavailable" in detail or "slot_unavailable" in detail


def test_p11_create_without_resource_id_regression(
    client,
    synced_catalog,
    cliente_exemplo,
    db,
    enable_booking_and_resource,
    booking_headers,
):
    """Regressão P01 — create sem resource_id permanece válido com resource engine ON."""
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
    assert response.json()["status"] == "pending_payment"


def test_p11_flag_off_uses_legacy_slot_conflict(
    client,
    synced_catalog,
    cliente_exemplo,
    db,
    enable_booking_only,
    booking_headers,
):
    """P11 flag OFF — conflito de slot legado ainda retorna 409 (paridade)."""
    from app.services.disponibilidade_service import DisponibilidadeService
    from app.modules.booking.application.commands.create_booking import (
        CreateBookingCommand,
        CreateBookingHandler,
    )

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=4),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    # Primeiro booking ocupa o slot
    first = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.horario.isoformat(),
        },
        headers=booking_headers(),
    )
    assert first.status_code == 201, first.text

    # Segundo no mesmo slot → 409
    second = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.horario.isoformat(),
            "resource_id": 999,
        },
        headers=booking_headers(),
    )
    assert second.status_code == 409, second.text
