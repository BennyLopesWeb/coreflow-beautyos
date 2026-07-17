"""
Sincronização Strangler Fig — ``inventory_items`` → ``core_assets`` + ``core_inventory``.
"""
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.inventory_item import InventoryItem
from app.modules.asset.domain.models import CoreAsset
from app.modules.inventory.models import CoreInventory

logger = get_logger("asset_sync")


class AssetLegacySyncService:
    """
    Sincroniza estoque legado para metamodelo Asset + Inventory.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza todos os itens de estoque legados.

        Returns:
            Quantidade processada.
        """
        rows = (
            self.db.query(InventoryItem)
            .filter(InventoryItem.deleted_at.is_(None))
            .all()
        )
        count = 0
        for item in rows:
            if self._upsert(item):
                count += 1
        self.db.commit()
        logger.info(f"Sync assets/inventory: {count}")
        return count

    def sync_one(self, inventory_item_id: int) -> Optional[Tuple[CoreAsset, CoreInventory]]:
        """
        Sincroniza um item de estoque específico.

        Args:
            inventory_item_id: ID ``inventory_items``.

        Returns:
            Tupla (CoreAsset, CoreInventory) ou None.
        """
        item = (
            self.db.query(InventoryItem)
            .filter(
                InventoryItem.id == inventory_item_id,
                InventoryItem.deleted_at.is_(None),
            )
            .first()
        )
        if not item:
            return None
        result = self._upsert(item)
        self.db.commit()
        return result

    def _upsert(self, item: InventoryItem) -> Optional[Tuple[CoreAsset, CoreInventory]]:
        """
        Cria ou atualiza core_asset e core_inventory.

        Args:
            item: Registro legado.

        Returns:
            Tupla (CoreAsset, CoreInventory).
        """
        asset_existing = (
            self.db.query(CoreAsset)
            .filter(CoreAsset.legacy_inventory_item_id == item.id)
            .first()
        )
        asset_payload = dict(
            company_id=item.company_id or 1,
            name=item.name,
            sku=item.sku,
            asset_type=item.asset_type,
            unit=item.unit,
            active=item.active,
            plugin_metadata={"source": "beauty", "legacy": "InventoryItem"},
        )
        if asset_existing:
            for key, val in asset_payload.items():
                setattr(asset_existing, key, val)
            asset = asset_existing
        else:
            asset = CoreAsset(legacy_inventory_item_id=item.id, **asset_payload)
            self.db.add(asset)
            self.db.flush()

        inv_existing = (
            self.db.query(CoreInventory)
            .filter(CoreInventory.legacy_inventory_item_id == item.id)
            .first()
        )
        inv_payload = dict(
            company_id=item.company_id or 1,
            asset_id=asset.id,
            quantity_on_hand=Decimal(str(item.quantity)),
            reorder_level=Decimal(str(item.reorder_level)),
        )
        if inv_existing:
            for key, val in inv_payload.items():
                setattr(inv_existing, key, val)
            inventory = inv_existing
        else:
            inventory = CoreInventory(
                legacy_inventory_item_id=item.id, **inv_payload
            )
            self.db.add(inventory)

        return asset, inventory
