"""
Model Payment (ReservationPayment)
Pagamentos persistidos: sinal e pagamento final.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    """Status do pagamento."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    # Legado
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    PAGO = "pago"
    CANCELADO = "cancelado"
    REEMBOLSADO = "reembolsado"


class PaymentType(str, enum.Enum):
    """Tipo de pagamento."""
    DEPOSIT = "deposit"
    FINAL_PAYMENT = "final_payment"
    REFUND = "refund"
    # Legado
    SINAL = "sinal"
    FINAL = "final"
    REEMBOLSO = "reembolso"


class Payment(Base):
    """
    Registro persistido de pagamento vinculado à reserva.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=False, index=True)
    tipo = Column(SQLEnum(PaymentType), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_id = Column(String(255), nullable=True, index=True)
    comprovante_url = Column(String(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agendamento = relationship("Agendamento", backref="payments")
