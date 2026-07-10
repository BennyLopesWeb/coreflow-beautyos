"""
Registro do Workflow Engine no event bus global.
"""
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from app.modules.workflow.engine.workflow_engine import workflow_engine
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus

logger = get_logger("workflow_handlers")


def _on_domain_event(event: DomainEvent) -> None:
    """
    Handler genérico — delega evento ao WorkflowEngine.

    Args:
        event: Evento de domínio publicado.

    Returns:
        None
    """
    db = SessionLocal()
    try:
        workflow_engine.process_event(db, event)
    except Exception as exc:
        logger.error(f"WorkflowEngine falhou para {event.event_type}: {exc}")
    finally:
        db.close()


def register_workflow_handlers() -> None:
    """
    Carrega workflows YAML e registra handlers no event bus.

    Returns:
        None
    """
    loaded = workflow_engine.load_all()
    logger.info(f"WorkflowEngine: {loaded} definição(ões) carregada(s)")

    subscribed = set()
    for trigger in workflow_engine.all_triggers():
        if trigger in subscribed:
            continue
        event_bus.subscribe(trigger, _on_domain_event)
        subscribed.add(trigger)
        logger.debug(f"WorkflowEngine inscrito em: {trigger}")
