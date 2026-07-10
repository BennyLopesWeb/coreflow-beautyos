"""
KafkaEventAdapter — publicação/consumo de eventos CoreFlow (CF-14).

Adapter opcional para produção; complementa RabbitMQ no rollout gradual.
"""
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.domain_event import DomainEvent

logger = get_logger("kafka_adapter")

OutboxEventHandler = Callable[[DomainEvent, Optional[int]], None]

TOPIC_DEFAULT = "coreflow.events"


class KafkaEventAdapter:
    """
    Publica eventos de domínio em tópico Kafka para processamento assíncrono.

    Attributes:
        bootstrap_servers: Brokers Kafka (ex.: localhost:9092).
        topic: Nome do tópico.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: str = TOPIC_DEFAULT,
    ):
        """
        Args:
            bootstrap_servers: Lista de brokers separados por vírgula.
            topic: Tópico Kafka.
        """
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or settings.KAFKA_TOPIC
        self._producer = None
        self._consumer = None

    def _get_producer(self):
        """
        Lazy init do KafkaProducer.

        Returns:
            Instância KafkaProducer.

        Raises:
            ImportError: Se kafka-python não estiver instalado.
        """
        if self._producer is not None:
            return self._producer
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise ImportError("kafka-python não instalado — pip install kafka-python") from exc

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers.split(","),
            value_serializer=self._serialize_value,
            acks="all",
            retries=3,
        )
        return self._producer

    @staticmethod
    def _serialize_value(value: Any) -> bytes:
        """
        Serializa valor Kafka — bytes Avro passam direto, dict vira JSON.

        Args:
            value: Payload dict ou bytes Avro.

        Returns:
            Bytes serializados.
        """
        if isinstance(value, bytes):
            return value
        return json.dumps(value, default=str).encode("utf-8")

    def _get_consumer(self):
        """
        Lazy init do KafkaConsumer (group outbox-worker).

        Returns:
            Instância KafkaConsumer.
        """
        if self._consumer is not None:
            return self._consumer
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise ImportError("kafka-python não instalado — pip install kafka-python") from exc

        self._consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers.split(","),
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=1000,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        return self._consumer

    def close(self) -> None:
        """Fecha producer e consumer Kafka."""
        if self._producer is not None:
            self._producer.close()
            self._producer = None
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

    def publish(self, event: DomainEvent, outbox_id: Optional[int] = None) -> None:
        """
        Publica evento serializado no tópico Kafka.

        Args:
            event: Evento de domínio.
            outbox_id: ID do registro outbox associado.

        Returns:
            None
        """
        if settings.KAFKA_SCHEMA_REGISTRY_ENABLED:
            from app.shared.events.schema_registry import get_schema_registry

            registry = get_schema_registry()
            envelope = registry.envelope(event, outbox_id=outbox_id)
            if settings.KAFKA_SCHEMA_ENCODING == "avro":
                from app.shared.events.avro_codec import AvroEventCodec

                confluent_id = envelope.get("confluent_schema_id") or 1
                record = registry.build_avro_record(event)
                payload = AvroEventCodec().encode(
                    envelope["schema_id"],
                    record,
                    confluent_id,
                )
            else:
                payload = envelope
        else:
            payload = {
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
        producer = self._get_producer()
        future = producer.send(self.topic, payload)
        future.get(timeout=10)
        logger.info(
            f"[kafka] Publicado {event.event_type} outbox_id={outbox_id} → {self.topic}"
        )

    def consume_one(self, handler: OutboxEventHandler) -> bool:
        """
        Consome uma mensagem do tópico e delega ao handler.

        Mensagens incompatíveis são enviadas à DLQ quando ``KAFKA_DLQ_ENABLED``.

        Args:
            handler: Callable(event, outbox_id).

        Returns:
            True se processou mensagem ou registrou DLQ; False se timeout.
        """
        consumer = self._get_consumer()
        for message in consumer:
            event_type_hint = None
            try:
                payload: Dict[str, Any] = message.value
                event_type_hint = None
                if settings.KAFKA_SCHEMA_REGISTRY_ENABLED:
                    from app.shared.events.schema_registry import get_schema_registry

                    event, outbox_id = get_schema_registry().parse_envelope(payload)
                    event_type_hint = event.event_type
                else:
                    event_data = payload["event"]
                    occurred = event_data.get("occurred_at")
                    event = DomainEvent(
                        event_id=event_data["event_id"],
                        event_type=event_data["event_type"],
                        company_id=event_data["company_id"],
                        payload=event_data["payload"],
                        aggregate_id=event_data.get("aggregate_id"),
                        aggregate_type=event_data.get("aggregate_type"),
                        occurred_at=datetime.fromisoformat(occurred)
                        if occurred
                        else datetime.utcnow(),
                    )
                    outbox_id = payload.get("outbox_id")
                    event_type_hint = event.event_type
                handler(event, outbox_id)
                consumer.commit()
                return True
            except Exception as exc:
                if settings.KAFKA_DLQ_ENABLED:
                    self._send_to_dlq(
                        message,
                        exc,
                        event_type_hint=event_type_hint,
                    )
                    consumer.commit()
                    return True
                logger.error(f"[kafka] Erro ao processar mensagem: {exc}")
                raise
        return False

    def _send_to_dlq(
        self,
        message: Any,
        error: Exception,
        event_type_hint: Optional[str] = None,
    ) -> None:
        """
        Persiste mensagem falha na DLQ local e tópico Kafka.

        Args:
            message: Mensagem Kafka consumer.
            error: Exceção capturada.
            event_type_hint: Tipo do evento inferido, se disponível.

        Returns:
            None
        """
        from app.db.session import SessionLocal
        from app.shared.events.kafka_dlq import DlqReason, KafkaDlqService

        session = SessionLocal()
        try:
            KafkaDlqService(session).record(
                raw_payload=message.value,
                error=error,
                reason=self._classify_dlq_reason(error),
                event_type=event_type_hint,
                partition=getattr(message, "partition", None),
                offset=getattr(message, "offset", None),
            )
        finally:
            session.close()

    @staticmethod
    def _classify_dlq_reason(error: Exception):
        """
        Classifica exceção em DlqReason.

        Args:
            error: Exceção capturada no consume.

        Returns:
            Valor DlqReason adequado.
        """
        from app.shared.events.kafka_dlq import DlqReason

        message = str(error).lower()
        if "avro" in message or "magic byte" in message:
            return DlqReason.AVRO_DECODE_ERROR
        if "schema" in message or "payload inválido" in message:
            return DlqReason.SCHEMA_INCOMPATIBLE
        if "envelope" in message or "event_id" in message:
            return DlqReason.ENVELOPE_PARSE_ERROR
        if isinstance(error, ValueError):
            return DlqReason.ENVELOPE_PARSE_ERROR
        return DlqReason.HANDLER_ERROR


_adapter: Optional[KafkaEventAdapter] = None


def get_kafka_adapter() -> KafkaEventAdapter:
    """
    Retorna singleton do adapter Kafka.

    Returns:
        KafkaEventAdapter configurado.
    """
    global _adapter
    if _adapter is None:
        _adapter = KafkaEventAdapter()
    return _adapter
