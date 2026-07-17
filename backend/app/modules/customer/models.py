"""
Entidade ORM Customer genérico CoreFlow.

Tabela ``core_customers`` espelha ``clientes`` via Strangler Fig.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CoreCustomer(Base):
    """
    Cliente final genérico CoreFlow (metamodelo: Customer).

    Espelha ``Cliente`` legado; novas integrações v1 referenciam este registro.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        name: Nome exibido.
        phone: Telefone (único por tenant).
        email: E-mail opcional.
        active: Cliente ativo.
        plugin_metadata: Campos extras do plugin.
        legacy_cliente_id: FK lógica ``clientes.id``.
    """

    __tablename__ = "core_customers"
    __table_args__ = (
        UniqueConstraint("legacy_cliente_id", name="uq_core_customer_legacy"),
        UniqueConstraint("company_id", "phone", name="uq_core_customer_company_phone"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    plugin_metadata = Column(JSON, default=dict)
    legacy_cliente_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
