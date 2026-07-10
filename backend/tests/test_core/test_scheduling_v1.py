"""Testes API v1 CoreFlow — scheduling (Location, Worker, Resource, Availability)."""
from datetime import datetime, timedelta


def test_scheduling_sync_creates_defaults(db, default_company):
    """Sync cria location e resource padrão por tenant."""
    from app.modules.scheduling.application.legacy_sync_service import (
        SchedulingLegacySyncService,
    )
    from app.modules.scheduling.domain.models import CoreLocation, CoreResource

    SchedulingLegacySyncService(db).sync_all()
    location = (
        db.query(CoreLocation)
        .filter(CoreLocation.company_id == default_company.id)
        .first()
    )
    resource = (
        db.query(CoreResource)
        .filter(CoreResource.company_id == default_company.id)
        .first()
    )
    assert location is not None
    assert location.is_default is True
    assert resource is not None
    assert resource.capacity == 1


def test_v1_locations_list(client, synced_scheduling):
    """GET /v1/locations retorna unidade padrão."""
    location = synced_scheduling["location"]
    response = client.get("/v1/locations")
    assert response.status_code == 200
    data = response.json()
    assert any(row["id"] == location.id for row in data)


def test_v1_resources_list(client, synced_scheduling):
    """GET /v1/resources retorna recurso padrão."""
    resource = synced_scheduling["resource"]
    response = client.get("/v1/resources")
    assert response.status_code == 200
    data = response.json()
    assert any(row["id"] == resource.id for row in data)


def test_v1_scheduling_availability(client, synced_scheduling):
    """GET /v1/scheduling/availability retorna slots genéricos."""
    catalog = synced_scheduling["catalog"]
    offering = synced_scheduling["offering"]
    target = datetime.now() + timedelta(days=3)
    response = client.get(
        "/v1/scheduling/availability",
        params={
            "date": target.isoformat(),
            "catalog_id": catalog.id,
            "offering_id": offering.id,
        },
    )
    assert response.status_code == 200, response.text
    slots = response.json()
    assert len(slots) > 0
    assert "starts_at" in slots[0]
    assert "available" in slots[0]
    assert slots[0]["catalog_id"] == catalog.id
    assert slots[0]["offering_id"] == offering.id
