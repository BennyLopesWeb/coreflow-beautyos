"""
LegacyCancelPolicyAdapter — CancelPolicyPort com regra 24h UTC (R2-F2b).
"""
from datetime import datetime, timedelta, timezone

from app.modules.booking.application.ports.clock_port import ClockPort
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.value_objects.booking_types import BookingLifecycleStatus


class LegacyCancelPolicyAdapter:
    """
    Policy default: pending sempre; approved se ``now_utc <= starts_at_utc - 24h``.

    Args:
        None
    """

    def may_cancel(self, booking: Booking, clock: ClockPort) -> bool:
        """
        Avalia policy de cancelamento.

        Args:
            booking: Aggregate.
            clock: Relógio UTC.

        Returns:
            True se cancel permitido pela policy.

        Raises:
            ValidationError: Se datetime naive ou sem timezone.
        """
        if booking.status == BookingLifecycleStatus.PENDING:
            return True
        if booking.status != BookingLifecycleStatus.APPROVED:
            return False

        now_utc = self._ensure_utc(clock.now_utc())
        starts_utc = self._ensure_utc(booking.time_slot.starts_at)
        deadline = starts_utc - timedelta(hours=24)
        return now_utc <= deadline

    def _ensure_utc(self, value: datetime) -> datetime:
        """
        Normaliza datetime para UTC ou rejeita naive.

        Args:
            value: Datetime de entrada.

        Returns:
            Datetime aware em UTC.

        Raises:
            ValidationError: Se datetime inválido após normalização.
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
