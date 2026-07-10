"""
SystemClockAdapter — ClockPort via relógio do sistema (UTC).
"""
from datetime import datetime, timezone

from app.modules.booking.application.ports.clock_port import ClockPort


class SystemClockAdapter:
    """
    Implementação ClockPort usando UTC do sistema.

    Args:
        None
    """

    def now_utc(self) -> datetime:
        """
        Retorna instante atual timezone-aware em UTC.

        Returns:
            datetime UTC aware.
        """
        return datetime.now(timezone.utc)
