"""
Entidade ORM Inventory genérico CoreFlow.

Tabela ``core_inventory`` espelha quantidades de ``inventory_items``.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CoreInventory(Base):
    """
    Nível de estoque genérico CoreFlow (metamodelo: Inventory).

    Representa *quanto* existe de um ``CoreAsset``.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        asset_id: FK ``core_assets``.
        quantity_on_hand: Quantidade disponível.
        reorder_level: Nível mínimo para alerta.
        legacy_inventory_item_id: FK lógica ``inventory_items.id``.
    """

    __tablename__ = "core_inventory"
    __table_args__ = (
        UniqueConstraint("legacy_inventory_item_id", name="uq_core_inventory_legacy"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("core_assets.id"), nullable=False, index=True)
    quantity_on_hand = Column(Numeric(10, 2), nullable=False, default=0)
    reorder_level = Column(Numeric(10, 2), nullable=False, default=0)
    legacy_inventory_item_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
