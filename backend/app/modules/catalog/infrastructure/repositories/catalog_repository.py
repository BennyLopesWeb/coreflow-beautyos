"""
SQLAlchemy adapter para CatalogRepository (ADR-030 / R2-F3b).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.catalog.domain.models import CoreCatalog, CoreOffering


class SqlAlchemyCatalogRepository:
    """
    Persistência/leitura de ``core_catalogs`` e ``core_offerings``.

    Args:
        db: Sessão SQLAlchemy (Unit of Work por request).
    """

    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, catalog_id: int, company_id: int) -> Optional[CoreCatalog]:
        """
        Carrega catalog por id e tenant.

        Args:
            catalog_id: ID ``core_catalogs``.
            company_id: Tenant.

        Returns:
            CoreCatalog ou None.
        """
        return (
            self._db.query(CoreCatalog)
            .filter(
                CoreCatalog.id == catalog_id,
                CoreCatalog.company_id == company_id,
                CoreCatalog.deleted_at.is_(None),
            )
            .first()
        )

    def get_offering(
        self, offering_id: int, company_id: int
    ) -> Optional[CoreOffering]:
        """
        Carrega offering por id e tenant.

        Args:
            offering_id: ID ``core_offerings``.
            company_id: Tenant.

        Returns:
            CoreOffering ou None.
        """
        return (
            self._db.query(CoreOffering)
            .filter(
                CoreOffering.id == offering_id,
                CoreOffering.company_id == company_id,
                CoreOffering.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_company(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCatalog]:
        """
        Lista catálogos do tenant.

        Args:
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista ordenada por nome.
        """
        q = self._db.query(CoreCatalog).filter(
            CoreCatalog.company_id == company_id,
            CoreCatalog.deleted_at.is_(None),
        )
        if active_only:
            q = q.filter(CoreCatalog.active.is_(True))
        return q.order_by(CoreCatalog.name).all()

    def list_offerings(
        self,
        catalog_id: int,
        company_id: int,
        active_only: bool = True,
    ) -> List[CoreOffering]:
        """
        Lista offerings de um catalog.

        Args:
            catalog_id: ID do catalog.
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista ordenada por id.
        """
        q = self._db.query(CoreOffering).filter(
            CoreOffering.catalog_id == catalog_id,
            CoreOffering.company_id == company_id,
            CoreOffering.deleted_at.is_(None),
        )
        if active_only:
            q = q.filter(CoreOffering.active.is_(True))
        return q.order_by(CoreOffering.id).all()

    def save_catalog(self, catalog: CoreCatalog) -> CoreCatalog:
        """
        Persiste catalog (insert ou update).

        Args:
            catalog: Entidade ORM.

        Returns:
            CoreCatalog com id.
        """
        self._db.add(catalog)
        self._db.flush()
        self._db.refresh(catalog)
        return catalog

    def save_offering(self, offering: CoreOffering) -> CoreOffering:
        """
        Persiste offering (insert ou update).

        Args:
            offering: Entidade ORM.

        Returns:
            CoreOffering com id.
        """
        self._db.add(offering)
        self._db.flush()
        self._db.refresh(offering)
        return offering
