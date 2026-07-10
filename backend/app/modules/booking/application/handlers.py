"""
Handlers de eventos de booking — adapters reagem a eventos de domínio.
"""
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus
from app.modules.booking.domain.events import RESERVATION_CREATED, BOOKING_CREATED, DEPOSIT_CONFIRMED, BOOKING_APPROVED, BOOKING_REJECTED
from app.core.logging_config import get_logger

logger = get_logger("booking_handlers")


def _on_reservation_created(event: DomainEvent) -> None:
    """
    Reage à criação de reserva (notificações, audit, IA futura).

    Args:
        event: Evento reservation.created.
    """
    reservation_id = event.payload.get("reservation_id")
    logger.info(
        f"[booking] Reserva {reservation_id} criada "
        f"(company={event.company_id}) — handlers assíncronos futuros aqui"
    )
    # Fase B: delegar a NotificationModule via port ou fila RabbitMQ


def _on_booking_created(event: DomainEvent) -> None:
    """
    Reage à criação de booking genérico CoreFlow v1.

    Args:
        event: Evento booking.created.
    """
    booking_id = event.payload.get("booking_id")
    logger.info(
        f"[booking] CoreBooking {booking_id} criado "
        f"(company={event.company_id}) — automação IA/workflow futuros"
    )


def _on_booking_approved(event: DomainEvent) -> None:
    """
    Reage à aprovação de booking genérico CoreFlow v1.

    Args:
        event: Evento booking.approved.
    """
    logger.info(
        f"[booking] CoreBooking {event.payload.get('booking_id')} aprovado "
        f"(company={event.company_id})"
    )


def _on_booking_rejected(event: DomainEvent) -> None:
    """
    Reage à rejeição de booking genérico CoreFlow v1.

    Args:
        event: Evento booking.rejected.
    """
    logger.info(
        f"[booking] CoreBooking {event.payload.get('booking_id')} rejeitado "
        f"(company={event.company_id}) motivo={event.payload.get('reason')}"
    )


def register_booking_handlers() -> None:
    """
    Registra handlers do módulo booking no event bus global.

    Returns:
        None
    """
    event_bus.subscribe(RESERVATION_CREATED, _on_reservation_created)
    event_bus.subscribe(BOOKING_CREATED, _on_booking_created)
    event_bus.subscribe(DEPOSIT_CONFIRMED, _on_deposit_confirmed)
    event_bus.subscribe(BOOKING_APPROVED, _on_booking_approved)
    event_bus.subscribe(BOOKING_REJECTED, _on_booking_rejected)


def _on_deposit_confirmed(event: DomainEvent) -> None:
    """
    Reage à confirmação de sinal (payment.deposit.confirmed).

    Args:
        event: Evento de depósito confirmado.
    """
    logger.info(
        f"[payment] Depósito confirmado reserva={event.payload.get('agendamento_id')} "
        f"(company={event.company_id})"
    )
