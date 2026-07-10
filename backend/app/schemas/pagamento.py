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
    """Resposta após envio de comprovante de depósito."""
    agendamento_id: int
    comprovante_url: str
    mensagem: str

