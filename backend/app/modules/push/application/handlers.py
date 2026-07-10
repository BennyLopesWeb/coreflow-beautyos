"""
Handlers push — reagem a eventos outbox/event bus (CF-12).
"""
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.modules.booking.domain.events import (
    BOOKING_APPROVED,
    BOOKING_CREATED,
    BOOKING_REJECTED,
    DEPOSIT_CONFIRMED,
    RESERVATION_CREATED,
)
from app.modules.push.application.push_service import PushNotificationService
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus

logger = get_logger("push_handlers")

PUSH_EVENT_TYPES = (
    RESERVATION_CREATED,
    BOOKING_CREATED,
    BOOKING_APPROVED,
    BOOKING_REJECTED,
    DEPOSIT_CONFIRMED,
)


def _on_push_event(event: DomainEvent) -> None:
    """
    Handler genérico — envia push mobile com deep link para evento de domínio.

    Args:
        event: Evento publicado via outbox/event bus.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        logs = PushNotificationService(db).handle_domain_event(event)
        if logs:
            logger.info(
                f"[push] {len(logs)} push(es) enviada(s) para {event.event_type} "
                f"(company={event.company_id})"
            )
    except Exception as exc:
        logger.error(f"Push handler falhou para {event.event_type}: {exc}")
    finally:
        db.close()


def register_push_handlers() -> None:
    """
    Inscreve handlers push nos tipos de evento relevantes.

    Returns:
        None
    """
    for event_type in PUSH_EVENT_TYPES:
        event_bus.subscribe(event_type, _on_push_event)
        logger.debug(f"Push handler inscrito em: {event_type}")
