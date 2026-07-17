"""
ResourceRepository — port de persistência do aggregate Resource.
"""
from typing import List, Optional, Protocol

from app.modules.resource.domain.entities.resource import Resource


class ResourceRepository(Protocol):
    """
    Port de persistência Resource → core_resources.
    """

    def save(self, resource: Resource) -> Resource:
        """
        Persiste aggregate (insert ou update).

        Args:
            resource: Aggregate.

        Returns:
            Aggregate com id.
        """
        ...

    def get_by_id(self, resource_id: int, company_id: int) -> Optional[Resource]:
        """
        Carrega por id + tenant.

        Args:
            resource_id: ID.
            company_id: Tenant.

        Returns:
            Resource ou None.
        """
        ...

    def list_active(
        self, company_id: int, location_id: Optional[int] = None
    ) -> List[Resource]:
        """
        Lista ativos do tenant.

        Args:
            company_id: Tenant.
            location_id: Filtro opcional.

        Returns:
            Lista.
        """
        ...
