"""
Hook ``waitlist.promoted`` — SportsOS stub (no-op).
"""
from app.core.logging_config import get_logger
from app.core.plugin.hooks import WaitlistPromotedPayload

logger = get_logger("sports.hooks.waitlist_promoted")


def handle(payload: WaitlistPromotedPayload) -> None:
    """
    Stub no-op para waitlist.promoted no SportsOS.

    Args:
        payload: Payload tipado.

    Returns:
        None
    """
    logger.debug(
        "[sports] waitlist.promoted stub booking_id=%s", payload.booking_id
    )
