"""
Handlers de eventos Identity — audit e integrações futuras.
"""
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus
from app.modules.identity.domain.events import USER_REGISTERED, COMPANY_CREATED
from app.core.logging_config import get_logger

logger = get_logger("identity_handlers")


def _on_user_registered(event: DomainEvent) -> None:
    """
    Reage ao registro de usuário.

    Args:
        event: identity.user.registered
    """
    logger.info(
        f"[identity] Usuário registrado: {event.payload.get('email')} "
        f"(company={event.company_id})"
    )


def _on_company_created(event: DomainEvent) -> None:
    """
    Reage à criação de empresa.

    Args:
        event: identity.company.created
    """
    logger.info(
        f"[identity] Empresa criada: {event.payload.get('slug')} "
        f"(id={event.aggregate_id})"
    )


def register_identity_handlers() -> None:
    """
    Registra handlers do módulo Identity no event bus global.

    Returns:
        None
    """
    event_bus.subscribe(USER_REGISTERED, _on_user_registered)
    event_bus.subscribe(COMPANY_CREATED, _on_company_created)
