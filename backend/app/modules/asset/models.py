"""
Entidade ORM Asset genérico CoreFlow.

Tabela ``core_assets`` espelha definição de itens de ``inventory_items``.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CoreAsset(Base):
    """
    Ativo/insumo genérico CoreFlow (metamodelo: Asset).

    Representa *o que* é estocado (definição), não a quantidade.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        name: Nome do ativo.
        sku: Código SKU.
        asset_type: supply | equipment | consumable.
        unit: Unidade de medida.
        active: Ativo no catálogo.
        plugin_metadata: Metadados do plugin.
        legacy_inventory_item_id: FK lógica ``inventory_items.id``.
    """

    __tablename__ = "core_assets"
    __table_args__ = (
        UniqueConstraint("legacy_inventory_item_id", name="uq_core_asset_legacy_inventory"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    sku = Column(String(255), nullable=True, index=True)
    asset_type = Column(String(255), nullable=False, default="supply", index=True)
    unit = Column(String(255), nullable=False, default="un")
    active = Column(Boolean, default=True, nullable=False)
    plugin_metadata = Column(JSON, default=dict)
    legacy_inventory_item_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
