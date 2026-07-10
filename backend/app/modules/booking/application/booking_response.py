"""
Serialização de CoreBooking para resposta API / cache idempotência.
"""
from typing import Any, Dict

from app.schemas.coreflow_v1 import BookingResponse


def booking_to_response_dict(booking) -> Dict[str, Any]:
    """
    Converte CoreBooking ORM para dict JSON-serializável (BookingResponse).

    Args:
        booking: Instância CoreBooking com relações opcionais carregadas.

    Returns:
        Dict compatível com BookingResponse.model_dump().
    """
    status_val = booking.status.value if hasattr(booking.status, "value") else booking.status
    pay_val = (
        booking.payment_status.value
        if hasattr(booking.payment_status, "value")
        else booking.payment_status
    )
    dto = BookingResponse(
        id=booking.id,
        company_id=booking.company_id,
        customer_id=booking.customer_id,
        catalog_id=booking.catalog_id,
        offering_id=booking.offering_id,
        scheduled_at=booking.scheduled_at,
        approved_at=booking.approved_at,
        status=status_val,
        payment_status=pay_val,
        price_total=booking.price_total,
        deposit_amount=booking.deposit_amount,
        remaining_amount=booking.remaining_amount,
        deposit_paid=booking.deposit_paid,
        notes=booking.notes,
        legacy_agendamento_id=booking.legacy_agendamento_id,
        catalog_name=booking.catalog.name if booking.catalog else None,
        offering_name=booking.offering.name if booking.offering else None,
        created_at=booking.created_at,
    )
    return dto.model_dump(mode="json")
