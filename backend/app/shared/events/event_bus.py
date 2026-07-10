"""
Event Bus in-memory — Modular Monolith Fase A/B.

Substituível por RabbitMQ/Kafka adapter sem alterar publishers/handlers.
"""
from collections import defaultdict
from typing import Callable, Dict, List, Type

from app.shared.events.domain_event import DomainEvent
from app.core.logging_config import get_logger

logger = get_logger("event_bus")

EventHandler = Callable[[DomainEvent], None]


class InMemoryEventBus:
    """
    Barramento de eventos síncrono dentro do mesmo processo.

    Publica eventos para handlers registrados por ``event_type``.
    Preparado para evoluir para adapter assíncrono (RabbitMQ) mantendo a mesma interface.

    Attributes:
        _handlers: Mapa event_type → lista de handlers.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Registra handler para um tipo de evento.

        Args:
            event_type: Nome do evento (ex.: reservation.created).
            handler: Callable que recebe DomainEvent.
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registrado: {event_type} → {handler.__name__}")

    def publish(self, event: DomainEvent) -> None:
        """
        Publica evento para todos os handlers registrados.

        Args:
            event: Evento de domínio a propagar.

        Raises:
            Exception: Re-lança falha do handler (fail-fast no MVP).
        """
        handlers = self._handlers.get(event.event_type, [])
        logger.info(
            f"Evento publicado: {event.event_type} "
            f"(company={event.company_id}, id={event.event_id}) "
            f"→ {len(handlers)} handler(s)"
        )
        try:
            from app.core.architecture_metrics import ArchitectureMetricsStore

            ArchitectureMetricsStore.get().record_event_published(
                event.event_type, handler_count=len(handlers)
            )
        except Exception:
            pass
        for handler in handlers:
            handler(event)

    def clear(self) -> None:
        """Remove todos os handlers (útil em testes)."""
        self._handlers.clear()


# Instância global do monólito — futuro: injetar via DI / FastAPI Depends
event_bus = InMemoryEventBus()
