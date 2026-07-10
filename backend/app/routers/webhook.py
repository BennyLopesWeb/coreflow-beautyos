"""
Router de Webhooks
Endpoints para recebimento de webhooks externos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.webhook import WhatsAppMessage, WhatsAppWebhookResponse
from app.integrations.pix import PixService
from app.services.agendamento_service import AgendamentoService
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("webhook")

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


@router.post("/whatsapp", response_model=WhatsAppWebhookResponse)
def receber_mensagem_whatsapp(
    message: WhatsAppMessage,
    db: Session = Depends(get_db)
):
    """
    Recebe mensagem do WhatsApp
    Em produção, integrar com API real do WhatsApp (Twilio, Evolution API)
    """
    if not settings.WHATSAPP_WEBHOOK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Webhook WhatsApp não está habilitado"
        )
    
    logger.info(
        f"Mensagem WhatsApp recebida",
        extra={
            "from": message.from_number,
            "message_preview": message.message[:50] if message.message else None
        }
    )
    
    # Mock: apenas loga a mensagem recebida
    # Em produção, processar mensagem e responder automaticamente
    # Exemplo: buscar agendamentos, responder com horários disponíveis, etc.
    
    return WhatsAppWebhookResponse(
        received=True,
        message="Mensagem recebida com sucesso (mock)"
    )


@router.post("/pix")
def receber_webhook_pix(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Recebe webhook do gateway Pix
    Confirma pagamento automaticamente quando recebido
    """
    if not settings.PIX_MOCK_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Webhook Pix não está habilitado"
        )
    
    # Em produção, validar assinatura do webhook
    # body = await request.json()
    # transaction_id = body.get("transaction_id")
    # status_pagamento = body.get("status")
    
    # Mock: apenas loga
    logger.info("Webhook Pix recebido (mock)")
    
    # Em produção:
    # if status_pagamento == "pago":
    #     # Buscar agendamento pelo transaction_id
    #     # Confirmar pagamento automaticamente
    #     service = AgendamentoService(db)
    #     service.confirmar_sinal(agendamento_id)
    
    return {"status": "received"}

