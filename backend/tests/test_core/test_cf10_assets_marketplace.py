"""Testes CF-10 — Asset/Inventory + Marketplace + enforcement staging."""
from decimal import Decimal

from app.core.core_enforcement import CoreEnforcementMiddleware, resolve_enforcement_mode
from app.models.inventory_item import InventoryItem
from app.modules.asset.application.legacy_sync_service import AssetLegacySyncService
from app.modules.asset.domain.models import CoreAsset
from app.modules.inventory.domain.models import CoreInventory
from app.modules.marketplace.application.marketplace_service import MarketplaceService
from app.core.config import settings


def test_asset_inventory_sync(db, default_company):
    """Sync cria core_asset + core_inventory a partir de InventoryItem."""
    item = InventoryItem(
        company_id=default_company.id,
        name="Fio de jumbo",
        sku="JUMBO-001",
        asset_type="supply",
        unit="un",
        quantity=Decimal("50.00"),
        reorder_level=Decimal("10.00"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    AssetLegacySyncService(db).sync_one(item.id)
    asset = (
        db.query(CoreAsset)
        .filter(CoreAsset.legacy_inventory_item_id == item.id)
        .first()
    )
    inv = (
        db.query(CoreInventory)
        .filter(CoreInventory.legacy_inventory_item_id == item.id)
        .first()
    )
    assert asset is not None
    assert asset.name == "Fio de jumbo"
    assert inv is not None
    assert inv.quantity_on_hand == Decimal("50.00")
    assert inv.asset_id == asset.id


def test_v1_assets_and_inventory(client, admin_headers, db, default_company):
    """GET /v1/assets e /v1/inventory retornam dados sincronizados."""
    item = InventoryItem(
        company_id=default_company.id,
        name="Spray fixador",
        sku="SPRAY-01",
        asset_type="consumable",
        unit="un",
        quantity=Decimal("12.00"),
        reorder_level=Decimal("3.00"),
    )
    db.add(item)
    db.commit()

    assets = client.get("/v1/assets", headers=admin_headers)
    assert assets.status_code == 200
    assert len(assets.json()) >= 1

    inventory = client.get("/v1/inventory", headers=admin_headers)
    assert inventory.status_code == 200
    assert len(inventory.json()) >= 1


def test_marketplace_listings(client, admin_headers, default_company):
    """GET /v1/marketplace/listings retorna catálogo cloud + local."""
    response = client.get("/v1/marketplace/listings", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    beauty = next(l for l in data if l["plugin_id"] == "beauty")
    assert beauty["available_locally"] is True
    assert beauty["installed"] is True


def test_marketplace_install_beauty(client, admin_headers, db, default_company):
    """POST /v1/marketplace/install ativa plugin beauty no tenant."""
    response = client.post(
        "/v1/marketplace/install",
        json={"plugin_id": "beauty"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["plugin_id"] == "beauty"


def test_marketplace_install_preview_fails(client, admin_headers):
    """Plugin inexistente retorna 400."""
    response = client.post(
        "/v1/marketplace/install",
        json={"plugin_id": "nonexistent-plugin-xyz"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_staging_enforcement_defaults_block(monkeypatch):
    """APP_ENV=staging força enforcement block quando mode não explícito."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "")
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    assert resolve_enforcement_mode() == "block"


def test_staging_enforcement_explicit_warn(monkeypatch):
    """CORE_ENFORCEMENT_MODE=warn tem prioridade sobre staging."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "warn")
    monkeypatch.setattr(settings, "APP_ENV", "staging")
    assert resolve_enforcement_mode() == "warn"
