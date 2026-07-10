"""Testes do Event Bus — Event-Driven Architecture v3.0."""
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import InMemoryEventBus


def test_event_bus_publish_subscribe():
    """Publica evento e executa handler registrado."""
    bus = InMemoryEventBus()
    received = []

    def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe("test.event", handler)
    event = DomainEvent(
        event_type="test.event",
        company_id=1,
        payload={"key": "value"},
    )
    bus.publish(event)

    assert len(received) == 1
    assert received[0].payload["key"] == "value"
    assert received[0].company_id == 1


def test_reservation_created_event_factory():
    """Factory de evento booking gera payload correto."""
    from app.modules.booking.domain.events import reservation_created

    event = reservation_created(
        company_id=1,
        reservation_id=42,
        cliente_id=7,
        valor_sinal="150.00",
    )
    assert event.event_type == "reservation.created"
    assert event.aggregate_id == "42"
    assert event.payload["cliente_id"] == 7
