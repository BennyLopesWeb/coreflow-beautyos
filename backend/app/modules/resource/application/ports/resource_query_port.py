"""
ResourceQueryPort — leitura de resources (R2-F3).
"""
from datetime import datetime
from typing import List, Optional, Protocol

from app.modules.resource.domain.entities.resource import Resource


class ResourceQueryPort(Protocol):
    """
    Port de consulta de resources.

    Methods:
        get_by_id: Carrega por id + tenant.
        list_active: Lista ativos do tenant.
        check_availability: Slot livre para resource.
    """

    def get_by_id(self, resource_id: int, company_id: int) -> Optional[Resource]:
        """
        Carrega resource por id.

        Args:
            resource_id: ID core_resources.
            company_id: Tenant.

        Returns:
            Resource ou None.
        """
        ...

    def list_active(
        self, company_id: int, location_id: Optional[int] = None
    ) -> List[Resource]:
        """
        Lista resources ativos.

        Args:
            company_id: Tenant.
            location_id: Filtro opcional.

        Returns:
            Lista de Resource.
        """
        ...

    def check_availability(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        """
        Verifica se o resource está livre no intervalo.

        Args:
            company_id: Tenant.
            resource_id: ID core_resources.
            starts_at: Início.
            ends_at: Fim.

        Returns:
            True se disponível (sem conflito de capacity).
        """
        ...
