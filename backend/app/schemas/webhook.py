"""
Schemas de Webhook WhatsApp
DTOs para recebimento de mensagens do WhatsApp (mock)
"""
from pydantic import BaseModel
from typing import Optional


class WhatsAppMessage(BaseModel):
    """Schema de mensagem do WhatsApp"""
    from_number: str
    message: str
    timestamp: Optional[str] = None


class WhatsAppWebhookResponse(BaseModel):
    """Schema de resposta do webhook"""
    received: bool
    message: str

