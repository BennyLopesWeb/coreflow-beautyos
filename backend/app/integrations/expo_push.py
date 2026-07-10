"""
ExpoPushClient — integração com Expo Push API v2 (CF-13).
"""
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("expo_push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class ExpoPushClient:
    """
    Cliente HTTP para envio de notificações via Expo Push Service.

    Em dev (sem ``EXPO_PUSH_ACCESS_TOKEN`` ou token mock), simula envio local.
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Args:
            access_token: Token de acesso Expo (opcional; usa settings).
        """
        self.access_token = access_token or settings.EXPO_PUSH_ACCESS_TOKEN

    def is_live(self) -> bool:
        """
        Indica se o cliente usará a API real da Expo.

        Returns:
            True se token configurado e modo live habilitado.
        """
        return bool(
            settings.EXPO_PUSH_LIVE
            and self.access_token
            and settings.PUSH_NOTIFICATIONS_ENABLED
        )

    def should_mock_token(self, expo_push_token: str) -> bool:
        """
        Detecta tokens de desenvolvimento que não devem ir à API Expo.

        Args:
            expo_push_token: Token do dispositivo.

        Returns:
            True se deve usar mock local.
        """
        return expo_push_token.startswith("ExponentPushToken[dev-")

    def send(
        self,
        expo_push_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Envia uma notificação push para um dispositivo.

        Args:
            expo_push_token: Token Expo Push do dispositivo.
            title: Título da notificação.
            body: Corpo da mensagem.
            data: Payload extra (deep_link, event_type, etc.).

        Returns:
            Dict com ``status`` (enviada|mock|falha) e detalhes da resposta.
        """
        payload_data = {k: str(v) for k, v in (data or {}).items()}

        if not self.is_live() or self.should_mock_token(expo_push_token):
            logger.info(
                f"[expo] MOCK push → {expo_push_token[:28]}... "
                f"title={title!r} deep_link={payload_data.get('deep_link')}"
            )
            return {"status": "mock", "token": expo_push_token}

        message = {
            "to": expo_push_token,
            "title": title,
            "body": body,
            "data": payload_data,
            "sound": "default",
        }
        if payload_data.get("universal_link"):
            message["url"] = payload_data["universal_link"]

        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            response = httpx.post(
                EXPO_PUSH_URL,
                json=message,
                headers=headers,
                timeout=15.0,
            )
            response.raise_for_status()
            body_json = response.json()
            ticket_status = "enviada"
            if isinstance(body_json, dict) and body_json.get("data"):
                errors = [
                    item.get("status")
                    for item in body_json["data"]
                    if item.get("status") == "error"
                ]
                if errors:
                    ticket_status = "falha"
            logger.info(f"[expo] Push enviada → {expo_push_token[:28]}... status={ticket_status}")
            return {"status": ticket_status, "response": body_json}
        except Exception as exc:
            logger.error(f"[expo] Falha ao enviar push: {exc}")
            return {"status": "falha", "error": str(exc)}

    def send_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Envia lote de mensagens push (até 100 por request Expo).

        Args:
            messages: Lista de dicts com to, title, body, data.

        Returns:
            Lista de resultados por mensagem.
        """
        results: List[Dict[str, Any]] = []
        for message in messages:
            results.append(
                self.send(
                    expo_push_token=message["to"],
                    title=message.get("title", ""),
                    body=message.get("body", ""),
                    data=message.get("data"),
                )
            )
        return results
