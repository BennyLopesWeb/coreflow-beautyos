"""
SchemaRegistryService — registro JSON Schema para eventos Kafka (CF-15).

Padrão compatível com Confluent Schema Registry (schema_id + version envelope),
sem servidor externo — schemas em ``backend/schemas/events/*.json``.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.domain_event import DomainEvent

logger = get_logger("schema_registry")

SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas" / "events"


class SchemaRegistryService:
    """
    Carrega JSON Schemas de eventos e valida/envelope mensagens Kafka.

    Attributes:
        schemas: Mapa schema_id → definição JSON Schema.
    """

    def __init__(self, schemas_dir: Optional[Path] = None):
        """
        Args:
            schemas_dir: Diretório de schemas (default backend/schemas/events).
        """
        self.schemas_dir = schemas_dir or SCHEMAS_DIR
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        """
        Escaneia diretório e carrega todos os arquivos *.json.

        Returns:
            None
        """
        self._schemas.clear()
        if not self.schemas_dir.is_dir():
            logger.warning(f"Diretório schemas não encontrado: {self.schemas_dir}")
            return
        for path in sorted(self.schemas_dir.glob("*.json")):
            schema_id = path.stem
            with open(path, encoding="utf-8") as handle:
                self._schemas[schema_id] = json.load(handle)
            logger.debug(f"Schema carregado: {schema_id}")

    def list_schemas(self) -> List[Dict[str, Any]]:
        """
        Lista schemas registrados com metadados.

        Returns:
            Lista de dicts com schema_id, title e required fields.
        """
        result = []
        for schema_id, schema in sorted(self._schemas.items()):
            result.append(
                {
                    "schema_id": schema_id,
                    "title": schema.get("title", schema_id),
                    "required": schema.get("required", []),
                    "$id": schema.get("$id"),
                }
            )
        return result

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém JSON Schema por ID (ex.: booking.approved.v1).

        Args:
            schema_id: Identificador do schema.

        Returns:
            Schema dict ou None.
        """
        return self._schemas.get(schema_id)

    def schema_id_for_event(self, event_type: str) -> Optional[str]:
        """
        Resolve schema_id padrão para um event_type.

        Args:
            event_type: Nome do evento (ex.: booking.approved).

        Returns:
            schema_id ou None se não registrado.
        """
        candidate = f"{event_type}.v1"
        if candidate in self._schemas:
            return candidate
        for schema_id in self._schemas:
            if schema_id.startswith(f"{event_type}."):
                return schema_id
        return None

    def validate_payload(self, schema_id: str, payload: Dict[str, Any]) -> bool:
        """
        Valida payload contra campos required do JSON Schema (validação leve).

        Args:
            schema_id: ID do schema.
            payload: Dados do evento.

        Returns:
            True se válido.

        Raises:
            ValueError: Schema não encontrado ou campos obrigatórios ausentes.
        """
        schema = self.get_schema(schema_id)
        if not schema:
            raise ValueError(f"Schema não encontrado: {schema_id}")

        required = schema.get("required", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValueError(
                f"Payload inválido para {schema_id}: campos ausentes {missing}"
            )
        return True

    def envelope(
        self,
        event: DomainEvent,
        outbox_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Envelopa evento com metadados de schema (Confluent-compatible pattern).

        Args:
            event: Evento de domínio.
            outbox_id: ID outbox opcional.

        Returns:
            Dict pronto para serialização Kafka.

        Raises:
            ValueError: Schema não registrado ou payload inválido.
        """
        schema_id = self.schema_id_for_event(event.event_type)
        if not schema_id:
            raise ValueError(f"Nenhum schema registrado para {event.event_type}")

        if settings.KAFKA_SCHEMA_VALIDATE:
            self.validate_payload(schema_id, event.payload)

        base_envelope = {
            "schema_id": schema_id,
            "schema_version": 1,
            "encoding": settings.KAFKA_SCHEMA_ENCODING,
            "outbox_id": outbox_id,
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "company_id": event.company_id,
                "payload": event.payload,
                "aggregate_id": event.aggregate_id,
                "aggregate_type": event.aggregate_type,
                "occurred_at": event.occurred_at.isoformat(),
            },
        }

        if settings.KAFKA_SCHEMA_REGISTRY_MODE == "confluent":
            base_envelope.update(self._confluent_metadata(schema_id, event))

        return base_envelope

    def _confluent_metadata(
        self,
        schema_id: str,
        event: DomainEvent,
    ) -> Dict[str, Any]:
        """
        Resolve ou registra schema no Confluent Schema Registry.

        Args:
            schema_id: ID local do schema.
            event: Evento de domínio.

        Returns:
            Dict com confluent_schema_id e subject.
        """
        from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient

        client = ConfluentSchemaRegistryClient()
        subject = client.subject_for_event(event.event_type)
        confluent_id = client.get_latest_schema_id(subject)

        if confluent_id is None:
            if settings.KAFKA_SCHEMA_ENCODING == "avro":
                from app.shared.events.avro_codec import AvroEventCodec

                avro = AvroEventCodec().get_avro_schema(schema_id)
                if avro:
                    confluent_id = client.register_avro_schema(subject, json.dumps(avro))
            else:
                schema = self.get_schema(schema_id)
                if schema:
                    confluent_id = client.register_json_schema(subject, schema)

        return {
            "confluent_schema_id": confluent_id,
            "confluent_subject": subject,
        }

    def build_avro_record(self, event: DomainEvent) -> Dict[str, Any]:
        """
        Flatten event para record Avro (booking.approved etc.).

        Args:
            event: Evento de domínio.

        Returns:
            Dict flat para fastavro writer.
        """
        record = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "company_id": event.company_id,
            "occurred_at": event.occurred_at.isoformat(),
        }
        for key, value in event.payload.items():
            if key not in record:
                record[key] = value
        return record

    def parse_envelope(self, message: Dict[str, Any]) -> Tuple[DomainEvent, Optional[int]]:
        """
        Reconstrói DomainEvent a partir de mensagem envelopada Kafka.

        Args:
            message: Dict deserializado do Kafka.

        Returns:
            Tupla (DomainEvent, outbox_id).
        """
        from datetime import datetime

        if "schema_id" in message:
            schema_id = message["schema_id"]
            event_data = message["event"]
            if settings.KAFKA_SCHEMA_VALIDATE and schema_id:
                self.validate_payload(schema_id, event_data.get("payload", {}))
            outbox_id = message.get("outbox_id")
        else:
            event_data = message.get("event", message)
            outbox_id = message.get("outbox_id")

        occurred = event_data.get("occurred_at")
        event = DomainEvent(
            event_id=event_data["event_id"],
            event_type=event_data["event_type"],
            company_id=event_data["company_id"],
            payload=event_data["payload"],
            aggregate_id=event_data.get("aggregate_id"),
            aggregate_type=event_data.get("aggregate_type"),
            occurred_at=datetime.fromisoformat(occurred) if occurred else datetime.utcnow(),
        )
        return event, outbox_id

    def list_avro_coverage(self) -> List[Dict[str, Any]]:
        """
        Compara JSON Schemas locais com Avro (.avsc) disponíveis.

        Returns:
            Lista com schema_id, has_json, has_avro e event_type inferido.
        """
        from app.shared.events.avro_codec import AvroEventCodec

        avro_ids = {item["schema_id"] for item in AvroEventCodec().list_schemas()}
        coverage = []
        for schema_id in sorted(self._schemas.keys()):
            event_type = schema_id.rsplit(".v", 1)[0] if ".v" in schema_id else schema_id
            coverage.append(
                {
                    "schema_id": schema_id,
                    "event_type": event_type,
                    "has_json": True,
                    "has_avro": schema_id in avro_ids,
                    "complete": schema_id in avro_ids,
                }
            )
        return coverage

    def register_all_avro_to_confluent(self) -> List[Dict[str, Any]]:
        """
        Registra todos os schemas Avro locais no Confluent Schema Registry.

        Returns:
            Lista com subject, schema_id local e confluent_schema_id.

        Raises:
            RuntimeError: Se mode != confluent.
        """
        if settings.KAFKA_SCHEMA_REGISTRY_MODE != "confluent":
            raise RuntimeError("Confluent mode necessário para register_all_avro")

        from app.shared.events.avro_codec import AvroEventCodec
        from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient

        client = ConfluentSchemaRegistryClient()
        codec = AvroEventCodec()
        results = []

        for item in codec.list_schemas():
            schema_id = item["schema_id"]
            event_type = schema_id.rsplit(".v", 1)[0]
            subject = client.subject_for_event(event_type)
            avro = codec.get_avro_schema(schema_id)
            if not avro:
                continue
            existing = client.get_latest_schema_id(subject)
            confluent_id = existing or client.register_avro_schema(subject, json.dumps(avro))
            results.append(
                {
                    "schema_id": schema_id,
                    "subject": subject,
                    "confluent_schema_id": confluent_id,
                    "registered": existing is None,
                }
            )
        return results


_registry: Optional[SchemaRegistryService] = None


def get_schema_registry() -> SchemaRegistryService:
    """
    Retorna singleton do Schema Registry file-based.

    Returns:
        SchemaRegistryService inicializado.
    """
    global _registry
    if _registry is None:
        _registry = SchemaRegistryService()
    return _registry
