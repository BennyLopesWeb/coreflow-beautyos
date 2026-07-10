"""
Integração WhatsApp
Envio de mensagens automáticas via WhatsApp
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("whatsapp")


class WhatsAppService:
    """
    Service para integração com WhatsApp
    Envia mensagens automáticas (confirmação, lembretes, etc)
    """
    
    def __init__(self):
        self.enabled = settings.WHATSAPP_WEBHOOK_ENABLED
        self.api_url = settings.WHATSAPP_API_URL
        self.api_key = settings.WHATSAPP_API_KEY
    
    def enviar_mensagem(
        self,
        telefone: str,
        mensagem: str,
        tipo: str = "texto"
    ) -> Dict[str, Any]:
        """
        Envia mensagem via WhatsApp
        Retorna status do envio
        
        Em produção, integrar com Twilio, Evolution API, etc.
        """
        if not self.enabled:
            logger.warning("WhatsApp desabilitado, usando mock")
        
        # Mock: simula envio
        message_id = f"whatsapp_{datetime.now().timestamp()}"
        
        logger.info(
            f"[MOCK] Mensagem WhatsApp enviada",
            extra={
                "message_id": message_id,
                "telefone": telefone,
                "tipo": tipo,
                "mensagem_preview": mensagem[:50]
            }
        )
        
        # Em produção, implementar:
        # import requests
        # response = requests.post(
        #     f"{self.api_url}/messages",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={
        #         "to": telefone,
        #         "message": mensagem,
        #         "type": tipo
        #     }
        # )
        # return response.json()
        
        return {
            "message_id": message_id,
            "status": "enviada",
            "telefone": telefone
        }
    
    def enviar_confirmacao_agendamento(
        self,
        telefone: str,
        nome_cliente: str,
        data_hora: datetime,
        tipo_tranca: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de confirmação de agendamento
        """
        mensagem = f"""
✅ Agendamento Confirmado!

Olá {nome_cliente}!

Seu agendamento foi confirmado:
📅 Data: {data_hora.strftime('%d/%m/%Y')}
🕐 Horário: {data_hora.strftime('%H:%M')}
💇 Tipo: {tipo_tranca}

Aguardamos você!
        """.strip()
        
        return self.enviar_mensagem(telefone, mensagem)
    
    def enviar_lembrete_24h(
        self,
        telefone: str,
        nome_cliente: str,
        data_hora: datetime
    ) -> Dict[str, Any]:
        """
        Envia lembrete 24h antes do agendamento
        """
        mensagem = f"""
⏰ Lembrete de Agendamento

Olá {nome_cliente}!

Lembramos que você tem um agendamento amanhã:
📅 {data_hora.strftime('%d/%m/%Y às %H:%M')}

Nos vemos em breve!
        """.strip()
        
        return self.enviar_mensagem(telefone, mensagem)
    
    def enviar_lembrete_3h(
        self,
        telefone: str,
        nome_cliente: str,
        data_hora: datetime
    ) -> Dict[str, Any]:
        """
        Envia lembrete 3h antes do agendamento
        """
        mensagem = f"""
⏰ Lembrete de Agendamento

Olá {nome_cliente}!

Seu agendamento é hoje às {data_hora.strftime('%H:%M')}!

Te esperamos!
        """.strip()
        
        return self.enviar_mensagem(telefone, mensagem)
    
    def enviar_pesquisa_satisfacao(
        self,
        telefone: str,
        nome_cliente: str,
        link_pesquisa: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de pesquisa de satisfação
        """
        mensagem = f"""
📊 Pesquisa de Satisfação

Olá {nome_cliente}!

Gostaríamos de saber sua opinião sobre o atendimento:
{link_pesquisa}

Obrigada! 🙏
        """.strip()
        
        return self.enviar_mensagem(telefone, mensagem)

