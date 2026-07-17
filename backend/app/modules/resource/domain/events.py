"""
Factories de eventos do bounded context Resource (R2-F3).
"""
from typing import Any, Dict, Optional

from app.shared.events.domain_event import DomainEvent

RESOURCE_CREATED = "resource.created"
RESOURCE_UPDATED = "resource.updated"
RESOURCE_ALLOCATED = "resource.allocated"
RESOURCE_RELEASED = "resource.released"


def resource_created(
    company_id: int,
    resource_id: int,
    location_id: int,
    capacity: int,
    resource_type: str,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Factory para evento resource.created.

    Args:
        company_id: Tenant.
        resource_id: ID core_resources.
        location_id: Unidade.
        capacity: Capacidade.
        resource_type: Tipo canônico.
        correlation_id: Rastreio opcional.

    Returns:
        DomainEvent pronto para outbox.
    """
    return DomainEvent(
        event_type=RESOURCE_CREATED,
        company_id=company_id,
        aggregate_id=str(resource_id),
        aggregate_type="Resource",
        payload={
            "resource_id": resource_id,
            "location_id": location_id,
            "capacity": capacity,
            "resource_type": resource_type,
            "correlation_id": correlation_id,
        },
    )


def resource_updated(
    company_id: int,
    resource_id: int,
    changes: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Factory para evento resource.updated.

    Args:
        company_id: Tenant.
        resource_id: ID.
        changes: Campos alterados.
        correlation_id: Rastreio opcional.

    Returns:
        DomainEvent.
    """
    return DomainEvent(
        event_type=RESOURCE_UPDATED,
        company_id=company_id,
        aggregate_id=str(resource_id),
        aggregate_type="Resource",
        payload={
            "resource_id": resource_id,
            "changes": changes,
            "correlation_id": correlation_id,
        },
    )


def resource_allocated(
    company_id: int,
    resource_id: int,
    booking_id: int,
    starts_at: str,
    ends_at: str,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Factory para evento resource.allocated (booking create flag ON).

    Args:
        company_id: Tenant.
        resource_id: Resource alocado.
        booking_id: Booking associado.
        starts_at: Início ISO.
        ends_at: Fim ISO.
        correlation_id: Rastreio opcional.

    Returns:
        DomainEvent.
    """
    return DomainEvent(
        event_type=RESOURCE_ALLOCATED,
        company_id=company_id,
        aggregate_id=str(resource_id),
        aggregate_type="Resource",
        payload={
            "resource_id": resource_id,
            "booking_id": booking_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "correlation_id": correlation_id,
        },
    )


def resource_released(
    company_id: int,
    resource_id: int,
    booking_id: int,
    correlation_id: Optional[str] = None,
) -> DomainEvent:
    """
    Factory para evento resource.released (booking cancel flag ON).

    Args:
        company_id: Tenant.
        resource_id: Resource liberado.
        booking_id: Booking cancelado.
        correlation_id: Rastreio opcional.

    Returns:
        DomainEvent.
    """
    return DomainEvent(
        event_type=RESOURCE_RELEASED,
        company_id=company_id,
        aggregate_id=str(resource_id),
        aggregate_type="Resource",
        payload={
            "resource_id": resource_id,
            "booking_id": booking_id,
            "correlation_id": correlation_id,
        },
    )
