"""
LegacyCancelPolicyAdapter — CancelPolicyPort com janela configurável (FIX-CANCEL-POLICY-01).

Default de instalação permanece 24h; o valor efetivo é injetado pelo handler
após ``BookingPolicyResolver.resolve(booking.company_id)``.
"""
from datetime import datetime

from app.modules.booking.application.ports.clock_port import ClockPort
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.policy.cancel_window import (
    ensure_utc,
    may_cancel_for_lifecycle,
)


class LegacyCancelPolicyAdapter:
    """
    Policy de cancelamento: pending sempre; approved se dentro da janela N.

    Args:
        approved_min_hours_before: Horas mínimas antes de ``starts_at``
            (default 24 — instalação). Deve vir da política do tenant no
            path oficial.
    """

    def __init__(self, approved_min_hours_before: int = 24) -> None:
        """
        Inicializa o adapter com a janela configurada.

        Args:
            approved_min_hours_before: N da política (inteiro ≥ 0).

        Raises:
            ValueError: Se N for inválido.
        """
        if not isinstance(approved_min_hours_before, int) or isinstance(
            approved_min_hours_before, bool
        ):
            raise ValueError("approved_min_hours_before deve ser int")
        if approved_min_hours_before < 0:
            raise ValueError("approved_min_hours_before não pode ser negativo")
        self._approved_min_hours_before = approved_min_hours_before

    @property
    def approved_min_hours_before(self) -> int:
        """
        Retorna a janela N configurada neste adapter.

        Returns:
            Inteiro de horas mínimas antes do início.
        """
        return self._approved_min_hours_before

    def may_cancel(self, booking: Booking, clock: ClockPort) -> bool:
        """
        Avalia policy de cancelamento.

        Args:
            booking: Aggregate.
            clock: Relógio UTC injetado.

        Returns:
            True se cancel permitido pela policy de janela.
        """
        return may_cancel_for_lifecycle(
            booking.status,
            clock.now_utc(),
            booking.time_slot.starts_at,
            self._approved_min_hours_before,
        )

    def _ensure_utc(self, value: datetime) -> datetime:
        """
        Normaliza datetime para UTC (compatível com testes/callers legados).

        Args:
            value: Datetime de entrada.

        Returns:
            Datetime aware em UTC.
        """
        return ensure_utc(value)


# Alias explícito para consumidores futuros (PATCH / docs).
ConfigurableCancelPolicyAdapter = LegacyCancelPolicyAdapter
