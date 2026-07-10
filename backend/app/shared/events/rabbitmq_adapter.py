"""
RabbitMQEventAdapter — publicação/consumo de eventos CoreFlow (CF-13).

Adapter opcional; quando desabilitado, o outbox usa bus in-memory síncrono.
"""
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.shared.events.domain_event import DomainEvent

logger = get_logger("rabbitmq_adapter")

EventHandler = Callable[[DomainEvent], None]
OutboxEventHandler = Callable[[DomainEvent, Optional[int]], None]

QUEUE_NAME = "coreflow.events"


class RabbitMQEventAdapter:
    """
    Publica eventos de domínio em fila RabbitMQ para processamento assíncrono.

    Attributes:
        url: URL AMQP (amqp://guest:guest@localhost:5672/).
        queue: Nome da fila durable.
    """

    def __init__(self, url: Optional[str] = None, queue: str = QUEUE_NAME):
        """
        Args:
            url: URL de conexão RabbitMQ.
            queue: Nome da fila.
        """
        self.url = url or settings.RABBITMQ_URL
        self.queue = queue
        self._connection = None
        self._channel = None

    def _connect(self):
        """
        Abre conexão e canal RabbitMQ (lazy).

        Returns:
            None

        Raises:
            ImportError: Se pika não estiver instalado.
            Exception: Falha de conexão AMQP.
        """
        if self._channel is not None and self._channel.is_open:
            return
        try:
            import pika
        except ImportError as exc:
            raise ImportError("pika não instalado — pip install pika") from exc

        params = pika.URLParameters(self.url)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=self.queue, durable=True)

    def close(self) -> None:
        """Fecha conexão RabbitMQ se aberta."""
        if self._connection and self._connection.is_open:
            self._connection.close()
        self._connection = None
        self._channel = None

    def publish(self, event: DomainEvent, outbox_id: Optional[int] = None) -> None:
        """
        Publica evento serializado na fila RabbitMQ.

        Args:
            event: Evento de domínio.
            outbox_id: ID do registro outbox associado (para ack do worker).

        Returns:
            None
        """
        self._connect()
        body = json.dumps(
            {
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
            },
            default=str,
        )
        import pika

        self._channel.basic_publish(
            exchange="",
            routing_key=self.queue,
            body=body.encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info(
            f"[rabbitmq] Publicado {event.event_type} outbox_id={outbox_id} → {self.queue}"
        )

    def consume_one(self, handler: OutboxEventHandler) -> bool:
        """
        Consome uma mensagem da fila e delega ao handler.

        Args:
            handler: Callable que processa DomainEvent.

        Returns:
            True se processou mensagem; False se fila vazia (timeout).
        """
        self._connect()
        method_frame, _header_frame, body = self._channel.basic_get(queue=self.queue, auto_ack=False)
        if method_frame is None:
            return False

        try:
            payload: Dict[str, Any] = json.loads(body.decode("utf-8"))
            event_data = payload["event"]
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
            handler(event, payload.get("outbox_id"))
            self._channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            return True
        except Exception as exc:
            logger.error(f"[rabbitmq] Erro ao processar mensagem: {exc}")
            self._channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)
            raise


_adapter: Optional[RabbitMQEventAdapter] = None


def get_rabbitmq_adapter() -> RabbitMQEventAdapter:
    """
    Retorna singleton do adapter RabbitMQ.

    Returns:
        RabbitMQEventAdapter configurado.
    """
    global _adapter
    if _adapter is None:
        _adapter = RabbitMQEventAdapter()
    return _adapter
