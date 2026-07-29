"""
Entidade ORM Waitlist genérico CoreFlow.

Tabela ``core_waitlist`` espelha ``fila`` via Strangler Fig.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class CoreWaitlistStatus(str, enum.Enum):
    """Status de item na fila de espera genérica CoreFlow."""

    WAITING = "waiting"
    CONTACTED = "contacted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CoreWaitlist(Base):
    """
    Fila de espera genérica CoreFlow (metamodelo: Waitlist).

    Espelha ``Fila`` legado; clientes entram sem horário confirmado e aguardam aprovação.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        customer_id: FK ``core_customers`` (opcional durante transição).
        catalog_id: FK ``core_catalogs``.
        offering_id: FK ``core_offerings``.
        preferred_date: Data desejada.
        preferred_time: Horário desejado opcional.
        position: Posição FIFO na fila.
        status: waiting | contacted | approved | rejected | cancelled.
        booking_id: FK ``core_bookings`` quando aprovado.
        notes: Observações do cliente.
        same_day: Atendimento no mesmo dia.
        legacy_fila_id: FK lógica ``fila.id``.
        legacy_cliente_id: ID legado clientes.
        legacy_tranca_id: ID legado trancas.
        legacy_service_image_id: ID legado service_images.
        plugin_metadata: Metadados do plugin.
    """

    __tablename__ = "core_waitlist"
    __table_args__ = (
        UniqueConstraint("legacy_fila_id", name="uq_core_waitlist_legacy"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("core_customers.id"), nullable=True, index=True)
    catalog_id = Column(Integer, ForeignKey("core_catalogs.id"), nullable=True, index=True)
    offering_id = Column(Integer, ForeignKey("core_offerings.id"), nullable=True, index=True)
    preferred_date = Column(Date, nullable=False, index=True)
    preferred_time = Column(Time, nullable=True)
    position = Column(Integer, nullable=False, default=1)
    status = Column(
        enum_values(CoreWaitlistStatus),
        default=CoreWaitlistStatus.WAITING,
        nullable=False,
        index=True,
    )
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    notes = Column(String(255), nullable=True)
    same_day = Column(Boolean, default=False, nullable=False)
    legacy_fila_id = Column(Integer, nullable=True, index=True)
    legacy_cliente_id = Column(Integer, nullable=True, index=True)
    legacy_tranca_id = Column(Integer, nullable=True, index=True)
    legacy_service_image_id = Column(Integer, nullable=True, index=True)
    plugin_metadata = Column(JSON, default=dict)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
