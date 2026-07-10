"""
Integração Pix
Geração de cobranças Pix e verificação de pagamento
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("pix")


class PixService:
    """
    Service para integração com gateway Pix
    Gera QR Code e código Pix, verifica pagamento
    """
    
    def __init__(self):
        self.enabled = settings.PIX_MOCK_ENABLED
        self.api_url = settings.PIX_API_URL
        self.api_key = settings.PIX_API_KEY
        self.merchant_id = settings.PIX_MERCHANT_ID
    
    def criar_cobranca(
        self,
        valor: Decimal,
        descricao: str,
        expiracao_minutos: int = 30
    ) -> Dict[str, Any]:
        """
        Cria cobrança Pix
        Retorna QR Code, código Pix e ID da transação
        
        Em produção, integrar com Asaas, Mercado Pago, etc.
        """
        if not self.enabled:
            logger.warning("Pix desabilitado, usando mock")
        
        # Mock: gera dados simulados
        transaction_id = f"pix_{datetime.now().timestamp()}"
        qr_code = f"00020126580014BR.GOV.BCB.PIX0136{transaction_id}5204000053039865802BR5925TRANCAPRO SISTEMA6009SAO PAULO62070503***6304ABCD"
        pix_code = f"00020126580014BR.GOV.BCB.PIX0136{transaction_id}5204000053039865802BR5925TRANCAPRO SISTEMA6009SAO PAULO62070503***6304ABCD"
        
        expires_at = datetime.now() + timedelta(minutes=expiracao_minutos)
        
        logger.info(
            f"[MOCK] Cobrança Pix criada",
            extra={
                "transaction_id": transaction_id,
                "valor": str(valor),
                "descricao": descricao,
                "expires_at": expires_at.isoformat()
            }
        )
        
        # Em produção, implementar:
        # import requests
        # response = requests.post(
        #     f"{self.api_url}/cobrancas",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={
        #         "valor": float(valor),
        #         "descricao": descricao,
        #         "expiracao": expiracao_minutos
        #     }
        # )
        # data = response.json()
        # return {
        #     "transaction_id": data["id"],
        #     "qr_code": data["qr_code"],
        #     "pix_code": data["pix_code"],
        #     "expires_at": datetime.fromisoformat(data["expires_at"])
        # }
        
        return {
            "transaction_id": transaction_id,
            "qr_code": qr_code,
            "pix_code": pix_code,
            "expires_at": expires_at
        }
    
    def verificar_pagamento(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verifica status do pagamento Pix
        Retorna status e dados do pagamento
        """
        if not self.enabled:
            logger.warning("Pix desabilitado, usando mock")
        
        # Mock: simula verificação
        # Em produção, consultar gateway real
        logger.info(f"[MOCK] Verificando pagamento Pix: {transaction_id}")
        
        # Mock: retorna como pendente (em produção, consultar gateway)
        return {
            "status": "pendente",  # pendente, pago, expirado, cancelado
            "paid_at": None,
            "valor": None
        }
    
    def confirmar_pagamento(self, transaction_id: str) -> bool:
        """
        Confirma pagamento manualmente (para mock)
        Em produção, usar webhook do gateway
        """
        logger.info(f"[MOCK] Pagamento confirmado manualmente: {transaction_id}")
        return True

