"""R2-F1b — Idempotency-Key, correlation_id, paridade P12."""
import json
import uuid
from datetime import datetime, timedelta

import pytest

from app.shared.events.outbox import CoreEventOutbox
from app.shared.idempotency.models import IdempotencyKey
from app.shared.idempotency.request_hash import compute_request_hash
from app.modules.booking.domain.models import CoreBooking


def test_create_without_idempotency_key_returns_400(client, synced_catalog, cliente_exemplo):
    """POST /v1/bookings sem header retorna 400."""
    catalog, offering = synced_catalog
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": (datetime.now() + timedelta(days=10)).isoformat(),
        },
    )
    assert response.status_code == 400
    assert "idempotency_key_required" in response.text


def test_p12_idempotent_retry_same_key(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Paridade P12 — retry com mesma Idempotency-Key retorna mesmo booking."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=8),
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
    key = str(uuid.uuid4())
    headers = booking_headers(key=key)

    first = client.post("/v1/bookings", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    second = client.post("/v1/bookings", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db.query(CoreBooking).count() >= 1
    assert (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.idempotency_key == key)
        .count()
        == 1
    )


def test_idempotency_key_reused_different_body_409(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """Mesma key com body diferente retorna 409."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=9),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slots = [h for h in horarios if h.disponivel][:2]
    assert len(slots) >= 2
    key = str(uuid.uuid4())
    headers = booking_headers(key=key)

    first_payload = {
        "customer_id": cliente_exemplo.id,
        "catalog_id": catalog.id,
        "offering_id": offering.id,
        "scheduled_at": slots[0].horario.isoformat(),
    }
    first = client.post("/v1/bookings", json=first_payload, headers=headers)
    assert first.status_code == 201, first.text

    second_payload = {
        **first_payload,
        "scheduled_at": slots[1].horario.isoformat(),
    }
    second = client.post("/v1/bookings", json=second_payload, headers=headers)
    assert second.status_code == 409
    assert "idempotency_key_reused" in second.text


def test_correlation_id_in_outbox_on_create(
    client, synced_catalog, cliente_exemplo, db, booking_headers, enable_booking_core
):
    """Eventos HTTP-originated incluem correlation_id no payload outbox (flag ON)."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=11),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)
    corr = str(uuid.uuid4())
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.horario.isoformat(),
        },
        headers=booking_headers(correlation_id=corr),
    )
    assert response.status_code == 201, response.text
    booking_id = response.json()["id"]

    evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.created",
            CoreEventOutbox.aggregate_id == str(booking_id),
        )
        .first()
    )
    assert evt is not None
    payload = json.loads(evt.payload)
    assert payload.get("correlation_id") == corr


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled."""
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        lambda key: key == "booking.core.enabled",
    )


def test_compute_request_hash_stable():
    """Unit — hash determinístico para mesmo body."""
    body = {"a": 1, "b": 2}
    assert compute_request_hash(body) == compute_request_hash({"b": 2, "a": 1})


def test_idempotency_not_saved_on_projection_failure(
    db, synced_catalog, cliente_exemplo, default_company, monkeypatch, enable_booking_core
):
    """Falha projeção não persiste idempotency key."""
    from unittest.mock import MagicMock

    from app.modules.booking.application.commands.create_booking import (
        CreateBookingCommand,
        CreateBookingHandler,
    )
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=12),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)
    key = str(uuid.uuid4())
    payload = {
        "customer_id": cliente_exemplo.id,
        "catalog_id": catalog.id,
        "offering_id": offering.id,
        "scheduled_at": slot.horario.isoformat(),
    }

    handler = CreateBookingHandler(db)
    monkeypatch.setattr(
        handler.booking_port,
        "project_create_booking",
        MagicMock(side_effect=RuntimeError("projection failed")),
    )

    with pytest.raises(RuntimeError):
        handler.execute(
            CreateBookingCommand(
                customer_id=cliente_exemplo.id,
                catalog_id=catalog.id,
                offering_id=offering.id,
                scheduled_at=slot.horario,
                company_id=default_company.id,
                idempotency_key=key,
                request_hash=compute_request_hash(payload),
                correlation_id=str(uuid.uuid4()),
            )
        )
    assert db.query(IdempotencyKey).filter(IdempotencyKey.idempotency_key == key).count() == 0
