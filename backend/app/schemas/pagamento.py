"""
Schemas de Pagamento
DTOs para pagamento de sinal (mock)
"""
from pydantic import BaseModel
from typing import Optional


class PagamentoSinalRequest(BaseModel):
    """Schema para confirmação de pagamento do sinal"""
    agendamento_id: int
    transaction_id: Optional[str] = None  # ID da transação Pix


class PagamentoSinalResponse(BaseModel):
    """Schema de resposta de pagamento"""
    agendamento_id: int
    sinal_pago: bool
    mensagem: str


class ComprovanteUploadResponse(BaseModel):
    """
    Resposta após envio de comprovante de depósito (R4-F15).

    Attributes:
        booking_id: ID ``core_bookings.id`` do vínculo autoritativo.
        comprovante_url: URL pública do arquivo salvo.
        mensagem: Texto para exibição ao cliente.
        agendamento_id: Legado opcional (preenchido só se houver ponte).
    """
    booking_id: int
    comprovante_url: str
    mensagem: str
    agendamento_id: Optional[int] = None

