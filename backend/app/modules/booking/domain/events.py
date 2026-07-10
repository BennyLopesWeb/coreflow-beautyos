"""
Constantes e factories de eventos do bounded context Booking.
"""
from typing import Optional

from app.shared.events.domain_event import DomainEvent

RESERVATION_CREATED = "reservation.created"
BOOKING_CREATED = "booking.created"
RESERVATION_APPROVED = "reservation.approved"
BOOKING_APPROVED = "booking.approved"
BOOKING_REJECTED = "booking.rejected"
BOOKING_CANCELLED = "booking.cancelled"
DEPOSIT_CONFIRMED = "payment.deposit.confirmed"
PAYMENT_CONFIRMED = "payment.confirmed"


def reservation_created(
    company_id: int,
    reservation_id: int,
    cliente_id: int,
    valor_sinal: str,
) -> DomainEvent:
    """
    Factory para evento ReservationCreated.

    Args:
        company_id: Tenant BeautyOS.
        reservation_id: ID da reserva criada.
        cliente_id: ID do cliente.
        valor_sinal: Valor do sinal como string decimal.

    Returns:
        DomainEvent pronto para publicação.
    """
    return DomainEvent(
        event_type=RESERVATION_CREATED,
        company_id=company_id,
        aggregate_id=str(reservation_id),
        aggregate_type="Reservation",
        payload={
            "reservation_id": reservation_id,
            "cliente_id": cliente_id,
            "valor_sinal": valor_sinal,
        },
    )


def booking_created(
    company_id: int,
    booking_id: int,
    customer_id: int,
    catalog_id: int,
    offering_id: int,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Factory para evento booking.created (metamodelo CoreFlow v1).

    Args:
        company_id: Tenant.
        booking_id: ID core_bookings.
        customer_id: ID do cliente.
        catalog_id: ID core_catalogs.
        offering_id: ID core_offerings.
        legacy_agendamento_id: ID agendamento legado.

    Returns:
        DomainEvent pronto para publicação.
    """
    return DomainEvent(
        event_type=BOOKING_CREATED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "customer_id": customer_id,
            "catalog_id": catalog_id,
            "offering_id": offering_id,
            "legacy_agendamento_id": legacy_agendamento_id,
        },
    )


def reservation_created_alias(
    company_id: int,
    booking_id: int,
    customer_id: int,
    catalog_id: int,
    offering_id: int,
    legacy_agendamento_id: Optional[int] = None,
    deposit_amount: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Alias ADR-027 — ``reservation.created`` com payload superset de booking.

    Args:
        company_id: Tenant.
        booking_id: ID core_bookings.
        customer_id: ID cliente.
        catalog_id: ID catalog.
        offering_id: ID offering.
        legacy_agendamento_id: ID legado.
        deposit_amount: Valor sinal string para consumidores legados.

    Returns:
        DomainEvent alias reservation.created.
    """
    return DomainEvent(
        event_type=RESERVATION_CREATED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reservation_id": legacy_agendamento_id or booking_id,
            "customer_id": customer_id,
            "cliente_id": customer_id,
            "catalog_id": catalog_id,
            "offering_id": offering_id,
            "legacy_agendamento_id": legacy_agendamento_id,
            "valor_sinal": deposit_amount,
            "canonical_type": BOOKING_CREATED,
            "deprecated_alias": True,
        },
    )


def booking_approved(
    company_id: int,
    booking_id: int,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Factory para evento booking.approved (metamodelo CoreFlow v1).

    Args:
        company_id: Tenant.
        booking_id: ID core_bookings.
        legacy_agendamento_id: ID agendamento legado.

    Returns:
        DomainEvent pronto para publicação.
    """
    return DomainEvent(
        event_type=BOOKING_APPROVED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
        },
    )


def reservation_approved_alias(
    company_id: int,
    booking_id: int,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Alias ADR-027 — ``reservation.approved``.

    Args:
        company_id: Tenant.
        booking_id: ID core.
        legacy_agendamento_id: ID legado.
        correlation_id: Rastreio HTTP.
        version: Versão optimistic lock pós-transição.

    Returns:
        DomainEvent alias.
    """
    return DomainEvent(
        event_type=RESERVATION_APPROVED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reservation_id": legacy_agendamento_id or booking_id,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
            "canonical_type": BOOKING_APPROVED,
            "deprecated_alias": True,
        },
    )


def booking_rejected(
    company_id: int,
    booking_id: int,
    reason: str,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Factory para evento booking.rejected (metamodelo CoreFlow v1).

    Args:
        company_id: Tenant.
        booking_id: ID core_bookings.
        reason: Motivo da rejeição.
        legacy_agendamento_id: ID agendamento legado.

    Returns:
        DomainEvent pronto para publicação.
    """
    return DomainEvent(
        event_type=BOOKING_REJECTED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reason": reason,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
        },
    )


RESERVATION_REJECTED = "reservation.rejected"


def reservation_rejected_alias(
    company_id: int,
    booking_id: int,
    reason: str,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Alias ADR-027 — ``reservation.rejected``.

    Args:
        company_id: Tenant.
        booking_id: ID core.
        reason: Motivo.
        legacy_agendamento_id: ID legado.
        correlation_id: Rastreio.
        version: Versão pós-transição.

    Returns:
        DomainEvent alias.
    """
    return DomainEvent(
        event_type=RESERVATION_REJECTED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reservation_id": legacy_agendamento_id or booking_id,
            "reason": reason,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
            "canonical_type": BOOKING_REJECTED,
            "deprecated_alias": True,
        },
    )


RESERVATION_CANCELLED = "reservation.cancelled"


def booking_cancelled(
    company_id: int,
    booking_id: int,
    reason: Optional[str] = None,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Factory para evento booking.cancelled (R2-F2b).

    Args:
        company_id: Tenant.
        booking_id: ID core_bookings.
        reason: Motivo do cancelamento.
        legacy_agendamento_id: ID agendamento legado.
        correlation_id: Rastreio HTTP.
        version: Versão pós-transição.

    Returns:
        DomainEvent pronto para outbox.
    """
    return DomainEvent(
        event_type=BOOKING_CANCELLED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reason": reason,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
        },
    )


def reservation_cancelled_alias(
    company_id: int,
    booking_id: int,
    reason: Optional[str] = None,
    legacy_agendamento_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    version: Optional[int] = None,
) -> DomainEvent:
    """
    Alias ADR-027 — ``reservation.cancelled``.

    Args:
        company_id: Tenant.
        booking_id: ID core.
        reason: Motivo.
        legacy_agendamento_id: ID legado.
        correlation_id: Rastreio.
        version: Versão pós-transição.

    Returns:
        DomainEvent alias.
    """
    return DomainEvent(
        event_type=RESERVATION_CANCELLED,
        company_id=company_id,
        aggregate_id=str(booking_id),
        aggregate_type="Booking",
        correlation_id=correlation_id,
        payload={
            "booking_id": booking_id,
            "reservation_id": legacy_agendamento_id or booking_id,
            "reason": reason,
            "legacy_agendamento_id": legacy_agendamento_id,
            "version": version,
            "canonical_type": BOOKING_CANCELLED,
            "deprecated_alias": True,
        },
    )
