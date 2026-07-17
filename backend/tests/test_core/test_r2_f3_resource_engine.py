"""R2-F3 — Resource Engine unit + CRUD API."""
from datetime import datetime, timedelta

import pytest

from app.modules.resource.domain.entities.resource import Resource
from app.modules.resource.domain.exceptions import InvalidResourceCapacityError
from app.modules.resource.domain.services.resource_domain_service import (
    ResourceDomainService,
)
from app.modules.resource.infrastructure.adapters.resource_type_adapter import (
    PluginResourceTypeAdapter,
)


def test_resource_entity_capacity_invalid():
    """Unit — capacity < 1 rejeitada."""
    with pytest.raises(InvalidResourceCapacityError):
        Resource.create(
            company_id=1,
            location_id=1,
            name="Cadeira",
            slug="cadeira-1",
            resource_type="chair",
            capacity=0,
        )


def test_resource_deactivate_idempotent():
    """Unit — deactivate é idempotente."""
    resource = Resource.create(
        company_id=1,
        location_id=1,
        name="Cadeira A",
        slug="cadeira-a",
        resource_type="chair",
        capacity=1,
    )
    resource.deactivate()
    assert resource.active is False
    resource.deactivate()
    assert resource.active is False


def test_resource_type_port_resolves_chair():
    """Unit — ResourceTypePort resolve beauty chair."""
    adapter = PluginResourceTypeAdapter()
    resolved = adapter.resolve("beauty", "chair")
    assert resolved is not None
    assert resolved["id"] == "chair"
    assert resolved["default_capacity"] == 1


def test_resource_type_port_unknown():
    """Unit — tipo desconhecido retorna None (sem fallback genérico)."""
    adapter = PluginResourceTypeAdapter()
    assert adapter.resolve("beauty", "spaceship") is None


def test_resource_domain_create_unknown_type():
    """Unit — domain service rejeita tipo desconhecido."""
    domain = ResourceDomainService(type_port=PluginResourceTypeAdapter())
    from app.modules.resource.domain.exceptions import UnknownResourceTypeError

    with pytest.raises(UnknownResourceTypeError):
        domain.create(
            company_id=1,
            location_id=1,
            name="X",
            slug="x",
            resource_type="spaceship",
        )


@pytest.fixture
def enable_resource_engine(monkeypatch):
    """Ativa resource.engine.enabled."""
    monkeypatch.setattr(
        "app.modules.resource.application.commands.create_resource.feature_flags.is_enabled",
        lambda key: key == "resource.engine.enabled",
    )
    monkeypatch.setattr(
        "app.modules.resource.application.commands.update_resource.feature_flags.is_enabled",
        lambda key: key == "resource.engine.enabled",
    )
    monkeypatch.setattr(
        "app.modules.resource.application.commands.deactivate_resource.feature_flags.is_enabled",
        lambda key: key == "resource.engine.enabled",
    )


def test_crud_create_requires_flag(client, admin_headers, synced_scheduling):
    """CRUD POST retorna 501 quando flag OFF."""
    location = synced_scheduling["location"]
    response = client.post(
        "/v1/resources",
        json={
            "location_id": location.id,
            "name": "Cadeira Extra",
            "resource_type": "chair",
            "capacity": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 501
    body = response.json()
    msg = str(body.get("message") or body.get("detail") or "")
    assert "resource_engine_disabled" in msg


def test_crud_create_get_patch(
    client, admin_headers, synced_scheduling, enable_resource_engine, db
):
    """CRUD — POST 201, GET list, PATCH capacity."""
    location = synced_scheduling["location"]
    create = client.post(
        "/v1/resources",
        json={
            "location_id": location.id,
            "name": "Cadeira F3",
            "resource_type": "chair",
            "capacity": 1,
            "slug": "cadeira-f3",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "Cadeira F3"
    assert body["resource_type"] == "chair"
    resource_id = body["id"]

    listed = client.get("/v1/resources", headers=admin_headers)
    assert listed.status_code == 200
    assert any(r["id"] == resource_id for r in listed.json())

    patched = client.patch(
        f"/v1/resources/{resource_id}",
        json={"capacity": 2, "name": "Cadeira F3b"},
        headers=admin_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["capacity"] == 2
    assert patched.json()["name"] == "Cadeira F3b"

    from app.shared.events.outbox import CoreEventOutbox

    created_evt = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "resource.created",
            CoreEventOutbox.aggregate_id == str(resource_id),
        )
        .first()
    )
    assert created_evt is not None
