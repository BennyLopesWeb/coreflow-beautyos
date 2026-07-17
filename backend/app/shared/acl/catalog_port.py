"""
ACL — LegacyCatalogPort (ADR-030 / R2-F3b).

Traduz sync legado ↔ metamodelo Catalog sem regras de negócio.
"""
from typing import Optional, Protocol

from sqlalchemy.orm import Session

from app.modules.catalog.application.legacy_sync_service import LegacySyncService
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering


class LegacyCatalogPort(Protocol):
    """
    Port ACL para sincronização e resolução Catalog ↔ legado (Tranca/ServiceImage).

    Core modules dependem desta interface — não de ``LegacySyncService`` direto
    em código novo.
    """

    def sync_all(self) -> dict:
        """
        Sincroniza catalog/offering/booking a partir do legado.

        Returns:
            Dict com contagens por entidade.
        """
        ...

    def resolve_catalog_by_legacy_tranca(
        self, legacy_tranca_id: int, company_id: int
    ) -> Optional[CoreCatalog]:
        """
        Resolve CoreCatalog a partir de ``trancas.id``.

        Args:
            legacy_tranca_id: ID tranca legado.
            company_id: Tenant.

        Returns:
            CoreCatalog ou None.
        """
        ...

    def resolve_offering_by_legacy_image(
        self, legacy_service_image_id: int, company_id: int
    ) -> Optional[CoreOffering]:
        """
        Resolve CoreOffering a partir de ``service_images.id``.

        Args:
            legacy_service_image_id: ID modelo legado.
            company_id: Tenant.

        Returns:
            CoreOffering ou None.
        """
        ...


class LegacyCatalogAdapter:
    """
    Adapter ACL — encapsula ``LegacySyncService`` + ``CatalogRepository``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db
        self._sync = LegacySyncService(db)

    def sync_all(self) -> dict:
        """
        Delega sync completo ao LegacySyncService.

        Returns:
            Contagens por entidade.
        """
        return self._sync.sync_all()

    def resolve_catalog_by_legacy_tranca(
        self, legacy_tranca_id: int, company_id: int
    ) -> Optional[CoreCatalog]:
        """
        Busca catalog pelo FK legado.

        Args:
            legacy_tranca_id: ID tranca.
            company_id: Tenant.

        Returns:
            CoreCatalog ou None.
        """
        return (
            self._db.query(CoreCatalog)
            .filter(
                CoreCatalog.legacy_tranca_id == legacy_tranca_id,
                CoreCatalog.company_id == company_id,
                CoreCatalog.deleted_at.is_(None),
            )
            .first()
        )

    def resolve_offering_by_legacy_image(
        self, legacy_service_image_id: int, company_id: int
    ) -> Optional[CoreOffering]:
        """
        Busca offering pelo FK legado.

        Args:
            legacy_service_image_id: ID service image.
            company_id: Tenant.

        Returns:
            CoreOffering ou None.
        """
        return (
            self._db.query(CoreOffering)
            .filter(
                CoreOffering.legacy_service_image_id == legacy_service_image_id,
                CoreOffering.company_id == company_id,
                CoreOffering.deleted_at.is_(None),
            )
            .first()
        )
