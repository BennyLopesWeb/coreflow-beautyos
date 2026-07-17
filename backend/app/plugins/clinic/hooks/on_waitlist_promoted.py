"""
Hook ``waitlist.promoted`` — ClinicOS stub (no-op).
"""
from app.core.logging_config import get_logger
from app.core.plugin.hooks import WaitlistPromotedPayload

logger = get_logger("clinic.hooks.waitlist_promoted")


def handle(payload: WaitlistPromotedPayload) -> None:
    """
    Stub no-op para waitlist.promoted no ClinicOS.

    Args:
        payload: Payload tipado.

    Returns:
        None
    """
    logger.debug(
        "[clinic] waitlist.promoted stub booking_id=%s", payload.booking_id
    )
