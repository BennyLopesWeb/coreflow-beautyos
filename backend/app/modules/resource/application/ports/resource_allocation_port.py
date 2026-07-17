"""
ResourceAllocationPort — alocação/liberação de slots (R2-F3).
"""
from datetime import datetime
from typing import Optional, Protocol


class ResourceAllocationPort(Protocol):
    """
    Port para alocar/liberar capacity de um resource em um slot.
    """

    def allocate(
        self,
        company_id: int,
        resource_id: int,
        booking_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        """
        Aloca resource para booking (cria schedule block se necessário).

        Args:
            company_id: Tenant.
            resource_id: Resource.
            booking_id: Booking associado.
            starts_at: Início.
            ends_at: Fim.

        Returns:
            True se alocado; False se conflito.
        """
        ...

    def release(
        self,
        company_id: int,
        resource_id: int,
        booking_id: int,
    ) -> None:
        """
        Libera alocação associada ao booking.

        Args:
            company_id: Tenant.
            resource_id: Resource.
            booking_id: Booking cancelado.

        Returns:
            None
        """
        ...
