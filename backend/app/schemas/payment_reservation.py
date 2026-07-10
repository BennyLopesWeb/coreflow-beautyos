"""
Schemas de pagamentos persistidos.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.payment import PaymentStatus, PaymentType


class PaymentCreate(BaseModel):
    """Registro de pagamento."""
    agendamento_id: int
    tipo: PaymentType
    valor: Decimal
    transaction_id: Optional[str] = None


class PaymentResponse(BaseModel):
    """Resposta de pagamento."""
    id: int
    agendamento_id: int
    tipo: PaymentType
    valor: Decimal
    status: PaymentStatus
    transaction_id: Optional[str] = None
    comprovante_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DepositPaymentRequest(BaseModel):
    """Confirmação de pagamento do sinal."""
    agendamento_id: int
    transaction_id: Optional[str] = None
    comprovante_url: Optional[str] = None


class FinalPaymentRequest(BaseModel):
    """Confirmação de pagamento final."""
    agendamento_id: int
    transaction_id: Optional[str] = None
