"""
Entidades ORM do metamodelo CoreFlow — Catalog e Offering.

Tabelas ``core_catalogs`` e ``core_offerings`` espelham legado via Strangler Fig.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class CoreCatalog(Base):
    """
    Catálogo genérico CoreFlow (metamodelo: Catalog).

    No plugin beauty, corresponde a uma "Categoria" / ``Tranca`` legado.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        name: Nome exibido.
        slug: Identificador URL-safe.
        description: Descrição opcional.
        images: URLs de capa (JSON array).
        active: Visível no catálogo público.
        plugin_metadata: Campos extras do plugin (JSON).
        legacy_tranca_id: FK lógica para ``trancas.id`` (sync).
    """

    __tablename__ = "core_catalogs"
    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_core_catalog_company_slug"),
        UniqueConstraint("legacy_tranca_id", name="uq_core_catalog_legacy_tranca"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    images = Column(JSON, default=list)
    active = Column(Boolean, default=True, nullable=False)
    plugin_metadata = Column(JSON, default=dict)
    legacy_tranca_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CoreOffering(Base):
    """
    Oferta de serviço genérica CoreFlow (metamodelo: Offering).

    No plugin beauty, corresponde a um "Modelo" / ``ServiceImage`` legado.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        catalog_id: FK para ``core_catalogs``.
        name: Nome do modelo/serviço.
        description: Descrição opcional.
        price_total: Preço total.
        deposit_pct: Percentual de sinal (0.30 = 30%).
        deposit_amount: Valor do sinal calculado.
        duration_minutes: Duração em minutos.
        image_url: URL da imagem principal.
        active: Disponível para reserva.
        plugin_metadata: Campos extras do plugin.
        legacy_service_image_id: FK lógica para ``service_images.id``.
    """

    __tablename__ = "core_offerings"
    __table_args__ = (
        UniqueConstraint("legacy_service_image_id", name="uq_core_offering_legacy_image"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("core_catalogs.id"), nullable=False, index=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    price_total = Column(Numeric(10, 2), nullable=True)
    deposit_pct = Column(Numeric(5, 4), default=0.30)
    deposit_amount = Column(Numeric(10, 2), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    image_url = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    plugin_metadata = Column(JSON, default=dict)
    legacy_service_image_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    catalog = relationship("CoreCatalog", backref="offerings")
