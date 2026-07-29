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

    Aggregate valida lifecycle; port valida a janela configurável
    (``approved_min_hours_before`` via política do tenant).
    """

    def may_cancel(self, booking: "Booking", clock: "ClockPort") -> bool:
        """
        Indica se cancelamento é permitido pela policy de negócio.

        Args:
            booking: Aggregate carregado (pending sempre True; approved
                aplica ``now_utc <= starts_at - N hours``).
            clock: Relógio UTC injetado.

        Returns:
            True se policy permite cancel.
        """
        ...
