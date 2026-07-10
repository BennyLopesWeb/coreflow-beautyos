"""
CancelPolicyPort — regra de cancelamento approved (ADR-026 amendment).
"""
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.modules.booking.application.ports.clock_port import ClockPort
    from app.modules.booking.domain.entities.booking import Booking


class CancelPolicyPort(Protocol):
    """
    Valida constraints externas antes de cancelar booking approved.

    Aggregate valida lifecycle; port valida policy (24h window).
    """

    def may_cancel(self, booking: "Booking", clock: "ClockPort") -> bool:
        """
        Indica se cancelamento é permitido pela policy de negócio.

        Args:
            booking: Aggregate carregado (pending sempre True via domain; approved checa 24h).
            clock: Relógio UTC injetado.

        Returns:
            True se policy permite cancel.
        """
        ...
