"""
Entidade ORM Payment genérico CoreFlow.

Tabela ``core_payments`` espelha ``payments`` via Strangler Fig.
"""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class CorePaymentType(str, enum.Enum):
    """Tipo de pagamento genérico CoreFlow."""

    DEPOSIT = "deposit"
    FINAL_PAYMENT = "final_payment"
    REFUND = "refund"


class CorePaymentStatus(str, enum.Enum):
    """Status de pagamento genérico CoreFlow."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class CorePayment(Base):
    """
    Pagamento genérico CoreFlow (metamodelo: Payment).

    Espelha ``Payment`` legado vinculado a booking/reserva.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        booking_id: FK ``core_bookings`` (opcional durante transição).
        payment_type: deposit | final_payment | refund.
        amount: Valor.
        status: pending | paid | failed | refunded.
        transaction_id: ID externo (Pix, gateway).
        receipt_url: URL comprovante.
        paid_at: Data confirmação.
        legacy_payment_id: FK lógica ``payments.id``.
        legacy_agendamento_id: FK lógica ``agendamentos.id``.
    """

    __tablename__ = "core_payments"
    __table_args__ = (
        UniqueConstraint("legacy_payment_id", name="uq_core_payment_legacy"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    payment_type = Column(
        enum_values(CorePaymentType),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        enum_values(CorePaymentStatus),
        default=CorePaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    transaction_id = Column(String(255), nullable=True, index=True)
    receipt_url = Column(String(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    legacy_payment_id = Column(Integer, nullable=True, index=True)
    legacy_agendamento_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
