"""
Port de provedor de pagamento — Hexagonal Architecture v3.0.

O domain/application depende desta interface; adapters concretos ficam em infrastructure.
"""
from decimal import Decimal
from typing import Optional, Protocol
from dataclasses import dataclass


@dataclass
class PixChargeResult:
    """
    Resultado da criação de cobrança PIX.

    Attributes:
        transaction_id: ID externo do provedor.
        qr_code: Payload copia-e-cola ou QR.
        qr_code_url: URL da imagem QR (opcional).
        expires_at: Expiração ISO8601 (opcional).
    """

    transaction_id: str
    qr_code: str
    qr_code_url: Optional[str] = None
    expires_at: Optional[str] = None


class PaymentProviderPort(Protocol):
    """
    Porta para integração com provedores de pagamento (PIX, cartão).

    Implementações: MockPixAdapter, MercadoPagoAdapter, AsaasAdapter.
    """

    def create_deposit_charge(
        self,
        amount: Decimal,
        reference: str,
        description: str,
    ) -> PixChargeResult:
        """
        Cria cobrança de sinal (depósito).

        Args:
            amount: Valor em BRL.
            reference: Referência interna (ex.: reservation_id).
            description: Descrição exibida ao pagador.

        Returns:
            PixChargeResult com dados para pagamento.
        """
        ...

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Valida assinatura de webhook do provedor.

        Args:
            payload: Corpo bruto da requisição.
            signature: Header de assinatura.

        Returns:
            True se autêntico.
        """
        ...
