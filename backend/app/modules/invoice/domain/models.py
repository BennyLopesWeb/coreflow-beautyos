"""
Entidade ORM Invoice genérico CoreFlow.

Tabela ``core_invoices`` espelha entradas ``financeiro`` (receitas).
"""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class CoreInvoiceStatus(str, enum.Enum):
    """Status de fatura/recibo genérico CoreFlow."""

    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class CoreInvoice(Base):
    """
    Fatura/recibo genérico CoreFlow (metamodelo: Invoice).

    Espelha movimentos ``Financeiro`` tipo ENTRADA vinculados a reservas.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        order_id: FK ``core_orders`` (opcional).
        booking_id: FK ``core_bookings`` (opcional).
        invoice_number: Número legível (ex.: INV-0001).
        description: Descrição da entrada.
        amount: Valor.
        status: issued | paid | void.
        issued_at: Data de emissão.
        legacy_financeiro_id: FK lógica ``financeiro.id``.
        legacy_agendamento_id: FK lógica ``agendamentos.id``.
    """

    __tablename__ = "core_invoices"
    __table_args__ = (
        UniqueConstraint("legacy_financeiro_id", name="uq_core_invoice_legacy_financeiro"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("core_orders.id"), nullable=True, index=True)
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    invoice_number = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        enum_values(CoreInvoiceStatus),
        default=CoreInvoiceStatus.ISSUED,
        nullable=False,
        index=True,
    )
    issued_at = Column(DateTime(timezone=True), nullable=False)
    legacy_financeiro_id = Column(Integer, nullable=True, index=True)
    legacy_agendamento_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
