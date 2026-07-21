"""Testes API v1 CoreFlow — metamodelo Catalog/Booking."""
from datetime import datetime, timedelta


def test_sync_legacy_creates_catalog(db, tranca_exemplo):
    """Sync cria core_catalog a partir de Tranca."""
    from app.modules.catalog.application.legacy_sync_service import LegacySyncService
    from app.modules.catalog.domain.models import CoreCatalog

    LegacySyncService(db).sync_catalogs()
    row = (
        db.query(CoreCatalog)
        .filter(CoreCatalog.legacy_tranca_id == tranca_exemplo.id)
        .first()
    )
    assert row is not None
    assert row.name == tranca_exemplo.nome


def test_v1_catalogs_list(client, synced_catalog):
    """GET /v1/catalogs retorna catálogo sincronizado."""
    catalog, _ = synced_catalog
    response = client.get("/v1/catalogs")
    assert response.status_code == 200
    data = response.json()
    assert any(c["id"] == catalog.id for c in data)


def test_v1_catalog_offerings(client, synced_catalog):
    """GET /v1/catalogs/{id}/offerings."""
    catalog, offering = synced_catalog
    response = client.get(f"/v1/catalogs/{catalog.id}/offerings")
    assert response.status_code == 200
    data = response.json()
    assert any(o["id"] == offering.id for o in data)


def test_v1_create_booking(client, synced_catalog, cliente_exemplo, db, booking_headers, monkeypatch):
    """POST /v1/bookings cria via CQRS e sincroniza core_bookings (dual-write legado ON — R4-F2)."""
    from app.services.disponibilidade_service import DisponibilidadeService

    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        lambda key: key in ("booking.core.enabled", "booking.legacy.projection.enabled"),
    )

    catalog, offering = synced_catalog
    tranca_id = catalog.legacy_tranca_id
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=2),
        tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    payload = {
        "customer_id": cliente_exemplo.id,
        "catalog_id": catalog.id,
        "offering_id": offering.id,
        "scheduled_at": slot.horario.isoformat(),
    }
    response = client.post("/v1/bookings", json=payload, headers=booking_headers())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["catalog_id"] == catalog.id
    assert body["legacy_agendamento_id"] is not None
    assert body["status"] == "pending_payment"
