"""
Hook ``waitlist.promoted`` — BeautyOS (P10 / R2-F4).
"""
from app.core.logging_config import get_logger
from app.core.plugin.hooks import WaitlistPromotedPayload

logger = get_logger("beauty.hooks.waitlist_promoted")

# Contador in-process para testes de paridade P10
_INVOKE_COUNT = 0


def reset_invoke_count() -> None:
    """
    Zera contador de invocações (testes).

    Returns:
        None
    """
    global _INVOKE_COUNT
    _INVOKE_COUNT = 0


def get_invoke_count() -> int:
    """
    Retorna quantas vezes o handler foi invocado desde o último reset.

    Returns:
        Contagem inteira.
    """
    return _INVOKE_COUNT


def handle(payload: WaitlistPromotedPayload) -> None:
    """
    Handler tipado após promoção waitlist → booking.

    Em F4 registra telemetria/log; notificações ricas ficam em fases posteriores.

    Args:
        payload: ``WaitlistPromotedPayload`` (DTO, sem ORM).

    Returns:
        None
    """
    global _INVOKE_COUNT
    _INVOKE_COUNT += 1
    logger.info(
        "[beauty] waitlist.promoted waitlist_id=%s booking_id=%s company=%s",
        payload.waitlist_id,
        payload.booking_id,
        payload.company_id,
    )
