"""
PaymentQueryPort — fronteira read-only Booking → Payments (ADR-028).
"""
from typing import Protocol


class PaymentQueryPort(Protocol):
    """
    Port de leitura para verificar depósito sem acoplar ORM de Payment ao domínio.
    """

    def is_deposit_confirmed(self, booking_id: int, company_id: int) -> bool:
        """
        Indica se o sinal foi confirmado para permitir approve.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            True se depósito confirmado (paridade ``ag.sinal_pago``).
        """
        ...
