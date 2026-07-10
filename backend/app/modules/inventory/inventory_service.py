"""
Serviço read-only de Inventory genérico CoreFlow (Support CRUD).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.inventory.models import CoreInventory


class InventoryService:
    """
    Consultas de leitura para ``core_inventory``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_inventory(
        self,
        company_id: int,
        asset_id: Optional[int] = None,
        low_stock_only: bool = False,
    ) -> List[CoreInventory]:
        """
        Lista níveis de estoque do tenant.

        Args:
            company_id: Tenant.
            asset_id: Filtra por ativo core.
            low_stock_only: Se True, retorna apenas abaixo do reorder_level.

        Returns:
            Lista de CoreInventory.
        """
        query = self.db.query(CoreInventory).filter(
            CoreInventory.company_id == company_id,
            CoreInventory.deleted_at.is_(None),
        )
        if asset_id is not None:
            query = query.filter(CoreInventory.asset_id == asset_id)
        rows = query.order_by(CoreInventory.asset_id.asc()).all()
        if low_stock_only:
            return [
                row for row in rows if row.quantity_on_hand <= row.reorder_level
            ]
        return rows

    def get_inventory(self, inventory_id: int, company_id: int) -> CoreInventory:
        """
        Obtém registro de estoque por ID.

        Args:
            inventory_id: ID core_inventory.
            company_id: Tenant.

        Returns:
            CoreInventory.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CoreInventory)
            .filter(
                CoreInventory.id == inventory_id,
                CoreInventory.company_id == company_id,
                CoreInventory.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Inventory", str(inventory_id))
        return row
