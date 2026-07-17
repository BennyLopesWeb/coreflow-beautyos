"""
CatalogRepository port (ADR-030 / R2-F3b).
"""
from typing import List, Optional, Protocol

from app.modules.catalog.domain.models import CoreCatalog, CoreOffering


class CatalogRepository(Protocol):
    """
    Port de persistência/leitura de Catalog e Offering.

    Implementação: ``SqlAlchemyCatalogRepository`` em infrastructure.
    Tipos de retorno são ORM metamodelo (hexagonal lite — sem aggregate).

    Methods:
        get_by_id: Catalog por id + tenant.
        get_offering: Offering por id + tenant.
        list_by_company: Catálogos do tenant.
        list_offerings: Offerings de um catalog.
        save_catalog: Persiste catalog (upsert).
        save_offering: Persiste offering (upsert).
    """

    def get_by_id(self, catalog_id: int, company_id: int) -> Optional[CoreCatalog]:
        """
        Carrega catalog por id e tenant (não deletado).

        Args:
            catalog_id: ID ``core_catalogs``.
            company_id: Tenant.

        Returns:
            CoreCatalog ou None.
        """
        ...

    def get_offering(
        self, offering_id: int, company_id: int
    ) -> Optional[CoreOffering]:
        """
        Carrega offering por id e tenant (não deletado).

        Args:
            offering_id: ID ``core_offerings``.
            company_id: Tenant.

        Returns:
            CoreOffering ou None.
        """
        ...

    def list_by_company(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCatalog]:
        """
        Lista catálogos do tenant.

        Args:
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista de CoreCatalog.
        """
        ...

    def list_offerings(
        self,
        catalog_id: int,
        company_id: int,
        active_only: bool = True,
    ) -> List[CoreOffering]:
        """
        Lista offerings de um catalog no tenant.

        Args:
            catalog_id: ID do catalog.
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista de CoreOffering.
        """
        ...

    def save_catalog(self, catalog: CoreCatalog) -> CoreCatalog:
        """
        Persiste ou atualiza catalog.

        Args:
            catalog: Entidade ORM.

        Returns:
            CoreCatalog com id atribuído.
        """
        ...

    def save_offering(self, offering: CoreOffering) -> CoreOffering:
        """
        Persiste ou atualiza offering.

        Args:
            offering: Entidade ORM.

        Returns:
            CoreOffering com id atribuído.
        """
        ...
