"""
Typed hook payloads — Plugin Engine v1 (ADR-011 / R2-F4).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import FrozenSet, Optional

# Conjunto fechado de hooks v1 (ADR-011)
HOOK_NAMES: FrozenSet[str] = frozenset(
    {
        "booking.created",
        "booking.approved",
        "booking.rejected",
        "booking.cancelled",
        "waitlist.promoted",
        "catalog.offering.selected",
    }
)


@dataclass(frozen=True)
class BookingCreatedPayload:
    """
    Payload tipado do hook ``booking.created``.

    Args:
        company_id: Tenant.
        booking_id: ID ``core_bookings``.
        customer_id: ID cliente (legado ``clientes`` no path atual).
        catalog_id: ID catalog.
        offering_id: ID offering.
        correlation_id: Correlação opcional.
    """

    company_id: int
    booking_id: int
    customer_id: int
    catalog_id: int
    offering_id: int
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class BookingApprovedPayload:
    """
    Payload tipado do hook ``booking.approved``.

    Args:
        company_id: Tenant.
        booking_id: ID booking.
        correlation_id: Correlação opcional.
    """

    company_id: int
    booking_id: int
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class BookingRejectedPayload:
    """
    Payload tipado do hook ``booking.rejected``.

    Args:
        company_id: Tenant.
        booking_id: ID booking.
        reason: Motivo opcional.
        correlation_id: Correlação opcional.
    """

    company_id: int
    booking_id: int
    reason: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class BookingCancelledPayload:
    """
    Payload tipado do hook ``booking.cancelled``.

    Args:
        company_id: Tenant.
        booking_id: ID booking.
        correlation_id: Correlação opcional.
    """

    company_id: int
    booking_id: int
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class WaitlistPromotedPayload:
    """
    Payload tipado do hook ``waitlist.promoted`` (P10).

    Args:
        company_id: Tenant.
        waitlist_id: ID ``core_waitlist``.
        booking_id: Booking criado na promoção.
        customer_id: ID cliente legado usado no booking.
        catalog_id: Catalog.
        offering_id: Offering.
        scheduled_at: Horário confirmado.
        correlation_id: Correlação opcional.
    """

    company_id: int
    waitlist_id: int
    booking_id: int
    customer_id: int
    catalog_id: int
    offering_id: int
    scheduled_at: datetime
    correlation_id: Optional[str] = None


@dataclass(frozen=True)
class OfferingSelectedPayload:
    """
    Payload tipado do hook ``catalog.offering.selected``.

    Args:
        company_id: Tenant.
        catalog_id: Catalog.
        offering_id: Offering.
    """

    company_id: int
    catalog_id: int
    offering_id: int
