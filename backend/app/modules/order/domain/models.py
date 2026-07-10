"""
Entidade ORM Order genérico CoreFlow.

Tabela ``core_orders`` espelha snapshot comercial de bookings/agendamentos.
"""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class CoreOrderStatus(str, enum.Enum):
    """Status de pedido genérico CoreFlow."""

    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CoreOrder(Base):
    """
    Pedido comercial genérico CoreFlow (metamodelo: Order).

    Um pedido por booking/reserva durante a transição Strangler Fig.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        booking_id: FK ``core_bookings``.
        customer_id: FK ``clientes`` / customer legado.
        status: open | paid | cancelled | refunded.
        total_amount: Valor total snapshot.
        paid_amount: Valor já pago.
        currency: Moeda ISO (default BRL).
        legacy_agendamento_id: FK lógica ``agendamentos.id``.
    """

    __tablename__ = "core_orders"
    __table_args__ = (
        UniqueConstraint("legacy_agendamento_id", name="uq_core_order_legacy_agendamento"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    status = Column(
        enum_values(CoreOrderStatus),
        default=CoreOrderStatus.OPEN,
        nullable=False,
        index=True,
    )
    total_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="BRL")
    legacy_agendamento_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
