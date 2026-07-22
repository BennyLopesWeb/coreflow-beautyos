"""
Model Payment (ReservationPayment)
Pagamentos persistidos: sinal e pagamento final.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
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

    R4-F6 (bridge Payment→booking_id / ADR-024 sunset): ``agendamento_id``
    deixou de ser obrigatório — pagamentos de bookings core-only (criados
    via ``POST /v1/bookings`` desde R3-F2/R4-F3) não têm ``Agendamento``
    associado. ``booking_id`` (FK nullable ``core_bookings.id``) é o novo
    vínculo autoritativo nesses casos; ``agendamento_id`` permanece
    preenchido apenas para pagamentos históricos/legado. Um registro deve
    ter ao menos um dos dois preenchidos (não validado a nível de schema —
    responsabilidade de ``PaymentReservationService``).

    R4-F7 (decouple físico das FKs restantes / RFC-003 M11): a FK física
    para ``agendamentos.id`` foi removida (``agendamento_id`` permanece
    ``Integer`` simples, sem constraint) — mesma mudança aplicada em
    ``Schedule``/``SatisfactionSurvey``/``Fila``/``QueueEntry``/
    ``Financeiro``/``NotificationLog`` nesta release.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    # R4-F7: FK física para agendamentos.id removida — Integer simples,
    # mantido apenas para leitura histórica.
    agendamento_id = Column(Integer, nullable=True, index=True)
    # R4-F6: FK para core_bookings.id — vínculo autoritativo para pagamentos
    # de bookings core-only (sem Agendamento associado). Nullable para
    # preservar compatibilidade com pagamentos históricos ligados apenas a
    # agendamento_id.
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    tipo = Column(SQLEnum(PaymentType), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_id = Column(String(255), nullable=True, index=True)
    comprovante_url = Column(String(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
