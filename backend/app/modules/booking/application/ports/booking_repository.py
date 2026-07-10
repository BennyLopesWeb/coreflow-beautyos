"""
CoreBookingRepository port (ADR-030).
"""
from typing import Optional, Protocol

from app.modules.booking.domain.entities.booking import Booking


class CoreBookingRepository(Protocol):
    """
    Port de persistência do aggregate Booking.

    Implementações vivem em ``infrastructure/repositories/``.
    """

    def save(self, booking: Booking) -> Booking:
        """
        Persiste ou atualiza booking.

        Args:
            booking: Aggregate com ou sem id.

        Returns:
            Booking com id atribuído.
        """
        ...

    def get_by_id(self, booking_id: int, company_id: int) -> Optional[Booking]:
        """
        Carrega aggregate por id e tenant.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            Booking ou None.
        """
        ...
