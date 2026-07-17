"""
Queries de catálogo — facade sobre CatalogRepository (R2-F3b).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.modules.catalog.infrastructure.repositories.catalog_repository import (
    SqlAlchemyCatalogRepository,
)


class CatalogQueryService:
    """
    Consultas read-only sobre catálogo genérico CoreFlow.

    Delega ao ``CatalogRepository`` (ADR-030). API pública estável para routers.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self._repo = SqlAlchemyCatalogRepository(db)

    def list_catalogs(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCatalog]:
        """
        Lista catálogos do tenant.

        Args:
            company_id: ID da empresa.
            active_only: Filtrar apenas ativos.

        Returns:
            Lista de CoreCatalog.
        """
        return self._repo.list_by_company(company_id, active_only=active_only)

    def get_catalog(self, catalog_id: int, company_id: Optional[int] = None) -> CoreCatalog:
        """
        Obtém catálogo por ID.

        Args:
            catalog_id: ID core_catalogs.
            company_id: Filtrar tenant opcional.

        Returns:
            CoreCatalog.

        Raises:
            NotFoundError: Se não existir.
        """
        if company_id is not None:
            row = self._repo.get_by_id(catalog_id, company_id)
        else:
            row = (
                self.db.query(CoreCatalog)
                .filter(
                    CoreCatalog.id == catalog_id,
                    CoreCatalog.deleted_at.is_(None),
                )
                .first()
            )
        if not row:
            raise NotFoundError("Catalog", str(catalog_id))
        return row

    def list_offerings(
        self,
        catalog_id: int,
        company_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[CoreOffering]:
        """
        Lista offerings de um catálogo.

        Args:
            catalog_id: ID do catálogo.
            company_id: Filtrar tenant.
            active_only: Apenas ativos reserváveis.

        Returns:
            Lista de CoreOffering.
        """
        self.get_catalog(catalog_id, company_id)
        if company_id is not None:
            return self._repo.list_offerings(
                catalog_id, company_id, active_only=active_only
            )
        q = self.db.query(CoreOffering).filter(
            CoreOffering.catalog_id == catalog_id,
            CoreOffering.deleted_at.is_(None),
        )
        if active_only:
            q = q.filter(CoreOffering.active.is_(True))
        return q.order_by(CoreOffering.id).all()

    def get_offering(
        self, offering_id: int, company_id: Optional[int] = None
    ) -> CoreOffering:
        """
        Obtém offering por ID.

        Args:
            offering_id: ID core_offerings.
            company_id: Filtrar tenant.

        Returns:
            CoreOffering.

        Raises:
            NotFoundError: Se não existir.
        """
        if company_id is not None:
            row = self._repo.get_offering(offering_id, company_id)
        else:
            row = (
                self.db.query(CoreOffering)
                .filter(
                    CoreOffering.id == offering_id,
                    CoreOffering.deleted_at.is_(None),
                )
                .first()
            )
        if not row:
            raise NotFoundError("Offering", str(offering_id))
        return row
