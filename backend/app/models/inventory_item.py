"""
Model InventoryItem — estoque legado BeautyOS (insumos, materiais).
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.base import Base


class InventoryItem(Base):
    """
    Item de estoque legado vinculado ao tenant.

    Espelhado para ``core_assets`` + ``core_inventory`` via Strangler Fig.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        name: Nome do item (ex.: Cabelo sintético premium).
        sku: Código SKU opcional.
        asset_type: Tipo genérico (supply, equipment, consumable).
        unit: Unidade (un, m, kg).
        quantity: Quantidade em estoque.
        reorder_level: Nível mínimo para reposição.
        active: Item ativo no catálogo de estoque.
    """

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=True, index=True)
    asset_type = Column(String, nullable=False, default="supply")
    unit = Column(String, nullable=False, default="un")
    quantity = Column(Numeric(10, 2), nullable=False, default=0)
    reorder_level = Column(Numeric(10, 2), nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
