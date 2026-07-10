"""
Service de seed — itens de estoque padrão BeautyOS para demo.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventory_item import InventoryItem


class InventorySeedService:
    """
    Garante itens de estoque demo para tenants BeautyOS.

    Args:
        db: Sessão SQLAlchemy.
    """

    DEFAULT_ITEMS = (
        {
            "name": "Cabelo sintético premium",
            "sku": "HAIR-SYN-PREM",
            "asset_type": "supply",
            "unit": "m",
            "quantity": Decimal("120.00"),
            "reorder_level": Decimal("20.00"),
        },
        {
            "name": "Gel edge control",
            "sku": "GEL-EDGE-01",
            "asset_type": "consumable",
            "unit": "un",
            "quantity": Decimal("15.00"),
            "reorder_level": Decimal("5.00"),
        },
        {
            "name": "Pente separador profissional",
            "sku": "TOOL-COMB-01",
            "asset_type": "equipment",
            "unit": "un",
            "quantity": Decimal("8.00"),
            "reorder_level": Decimal("2.00"),
        },
    )

    def __init__(self, db: Session):
        self.db = db

    def ensure_default_items(self, company_id: int) -> int:
        """
        Cria itens demo se o tenant ainda não tiver estoque.

        Args:
            company_id: ID da empresa.

        Returns:
            Quantidade de itens criados nesta execução.
        """
        existing = (
            self.db.query(InventoryItem)
            .filter(
                InventoryItem.company_id == company_id,
                InventoryItem.deleted_at.is_(None),
            )
            .count()
        )
        if existing > 0:
            return 0

        created = 0
        for item in self.DEFAULT_ITEMS:
            self.db.add(
                InventoryItem(
                    company_id=company_id,
                    name=item["name"],
                    sku=item["sku"],
                    asset_type=item["asset_type"],
                    unit=item["unit"],
                    quantity=item["quantity"],
                    reorder_level=item["reorder_level"],
                    active=True,
                )
            )
            created += 1
        self.db.commit()
        return created
