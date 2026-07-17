"""
Hook ``booking.created`` — BeautyOS stub (R2-F4).
"""
from app.core.logging_config import get_logger
from app.core.plugin.hooks import BookingCreatedPayload

logger = get_logger("beauty.hooks.booking_created")


def handle(payload: BookingCreatedPayload) -> None:
    """
    Handler tipado após criação de booking.

    Args:
        payload: ``BookingCreatedPayload``.

    Returns:
        None
    """
    logger.info(
        "[beauty] booking.created booking_id=%s company=%s",
        payload.booking_id,
        payload.company_id,
    )
