"""
ConfluentSchemaRegistryClient — integração HTTP com Schema Registry (CF-16).

Suporta registro e lookup de schemas JSON/Avro via API REST Confluent.
"""
import json
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("confluent_schema_registry")


class ConfluentSchemaRegistryClient:
    """
    Cliente HTTP para Confluent Schema Registry.

    Attributes:
        base_url: URL base (ex.: http://localhost:8081).
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Args:
            base_url: URL do Schema Registry (default settings).
        """
        self.base_url = (base_url or settings.KAFKA_SCHEMA_REGISTRY_URL).rstrip("/")

    def _headers(self) -> Dict[str, str]:
        """
        Monta headers HTTP incluindo auth básica opcional.

        Returns:
            Dict de headers.
        """
        headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        if settings.KAFKA_SCHEMA_REGISTRY_USER and settings.KAFKA_SCHEMA_REGISTRY_PASSWORD:
            import base64

            token = base64.b64encode(
                f"{settings.KAFKA_SCHEMA_REGISTRY_USER}:"
                f"{settings.KAFKA_SCHEMA_REGISTRY_PASSWORD}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {token}"
        return headers

    def subject_for_event(self, event_type: str) -> str:
        """
        Nome do subject Confluent para um event_type.

        Args:
            event_type: Ex.: booking.approved

        Returns:
            Subject no formato ``{event_type}-value``.
        """
        return f"{event_type}-value"

    def register_json_schema(self, subject: str, schema: Dict[str, Any]) -> int:
        """
        Registra JSON Schema no Confluent Schema Registry.

        Args:
            subject: Nome do subject.
            schema: JSON Schema document.

        Returns:
            schema_id atribuído pelo registry.

        Raises:
            httpx.HTTPError: Falha na API Confluent.
        """
        payload = {"schemaType": "JSON", "schema": json.dumps(schema)}
        url = f"{self.base_url}/subjects/{subject}/versions"
        response = httpx.post(url, json=payload, headers=self._headers(), timeout=15.0)
        response.raise_for_status()
        schema_id = int(response.json()["id"])
        logger.info(f"[confluent-sr] Registrado {subject} → id={schema_id}")
        return schema_id

    def register_avro_schema(self, subject: str, avro_schema: str) -> int:
        """
        Registra Avro schema (.avsc) no Confluent Schema Registry.

        Args:
            subject: Nome do subject.
            avro_schema: Conteúdo Avro schema como string JSON.

        Returns:
            schema_id atribuído pelo registry.
        """
        payload = {"schemaType": "AVRO", "schema": avro_schema}
        url = f"{self.base_url}/subjects/{subject}/versions"
        response = httpx.post(url, json=payload, headers=self._headers(), timeout=15.0)
        response.raise_for_status()
        schema_id = int(response.json()["id"])
        logger.info(f"[confluent-sr] Avro registrado {subject} → id={schema_id}")
        return schema_id

    def get_latest_schema_id(self, subject: str) -> Optional[int]:
        """
        Obtém ID da versão mais recente de um subject.

        Args:
            subject: Nome do subject.

        Returns:
            schema_id ou None se subject não existir.
        """
        url = f"{self.base_url}/subjects/{subject}/versions/latest"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=10.0)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return int(response.json()["id"])
        except httpx.HTTPError as exc:
            logger.warning(f"[confluent-sr] Lookup falhou {subject}: {exc}")
            return None

    def health_check(self) -> bool:
        """
        Verifica se o Schema Registry está acessível.

        Returns:
            True se GET /subjects retorna 200.
        """
        try:
            response = httpx.get(
                f"{self.base_url}/subjects",
                headers=self._headers(),
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def check_compatibility(
        self,
        subject: str,
        avro_schema: str,
        compatibility: str = "BACKWARD",
    ) -> Dict[str, Any]:
        """
        Verifica compatibilidade de schema Avro via API Confluent.

        Args:
            subject: Subject Confluent (ex.: booking.approved-value).
            avro_schema: Schema Avro serializado como JSON string.
            compatibility: Modo BACKWARD | FULL | FORWARD (default BACKWARD).

        Returns:
            Dict com is_compatible e detalhes da resposta.
        """
        url = f"{self.base_url}/compatibility/subjects/{subject}/versions/latest"
        headers = self._headers()
        headers["Content-Type"] = "application/vnd.schemaregistry.v1+json"
        payload = {"schema": avro_schema, "schemaType": "AVRO"}

        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                params={"verbose": "true"},
                timeout=15.0,
            )
            if response.status_code == 404:
                return {
                    "is_compatible": True,
                    "reason": "subject_not_found_first_registration",
                    "compatibility": compatibility,
                }
            response.raise_for_status()
            body = response.json()
            return {
                "is_compatible": body.get("is_compatible", False),
                "compatibility": compatibility,
                "messages": body.get("messages", []),
            }
        except httpx.HTTPError as exc:
            logger.warning(f"[confluent-sr] Compat check falhou {subject}: {exc}")
            return {"is_compatible": False, "error": str(exc), "compatibility": compatibility}
