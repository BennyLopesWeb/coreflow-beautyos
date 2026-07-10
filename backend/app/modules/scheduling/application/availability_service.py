"""
Scheduling engine genérico CoreFlow — disponibilidade de slots.

Usa ``SchedulingEngine`` (Resource + ScheduleBlock + capacity) com merge opcional
do adapter legado (Strangler Fig).
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.catalog.application.legacy_sync_service import LegacySyncService
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.modules.scheduling.application.scheduling_query_service import SchedulingQueryService
from app.modules.scheduling.engine.scheduling_engine import SchedulingEngine
from app.schemas.coreflow_v1 import AvailabilitySlotResponse


class SchedulingAvailabilityService:
    """
    Calcula slots disponíveis usando IDs genéricos CoreFlow.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.legacy_sync = LegacySyncService(db)
        self.scheduling_query = SchedulingQueryService(db)
        self.engine = SchedulingEngine(db)

    def get_availability(
        self,
        company_id: int,
        target_date: datetime,
        catalog_id: int,
        offering_id: int,
        resource_id: Optional[int] = None,
        worker_id: Optional[int] = None,
    ) -> List[AvailabilitySlotResponse]:
        """
        Retorna slots de disponibilidade para catalog/offering genéricos.

        Args:
            company_id: Tenant.
            target_date: Data base da consulta.
            catalog_id: ID core_catalogs.
            offering_id: ID core_offerings.
            resource_id: Recurso opcional.
            worker_id: Profissional opcional (informativo na resposta).

        Returns:
            Lista de slots com flag ``available``.

        Raises:
            NotFoundError: Entidades inválidas.
            BusinessRuleError: Regras de negócio.
        """
        catalog = self._get_catalog(catalog_id, company_id)
        offering = self._get_offering(offering_id, company_id, catalog.id)

        resolved_resource_id = self._resolve_resource_id(
            company_id, resource_id
        )
        resolved_worker_id = self._resolve_worker_id(company_id, worker_id)

        tranca_id, service_image_id = self.legacy_sync.resolve_legacy_ids(
            catalog.id, offering.id
        )

        duration = offering.duration_minutes or 30
        engine_slots = self.engine.check_availability(
            company_id=company_id,
            resource_id=resolved_resource_id,
            target_date=target_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            duration_minutes=duration,
            legacy_tranca_id=tranca_id,
            legacy_service_image_id=service_image_id,
            merge_legacy=True,
        )

        return [
            AvailabilitySlotResponse(
                starts_at=slot.starts_at,
                available=slot.available,
                duration_minutes=slot.duration_minutes,
                catalog_id=catalog.id,
                offering_id=offering.id,
                resource_id=resolved_resource_id,
                worker_id=resolved_worker_id,
            )
            for slot in engine_slots
        ]

    def _resolve_resource_id(
        self, company_id: int, resource_id: Optional[int]
    ) -> int:
        """
        Resolve resource_id informado ou default do tenant.

        Args:
            company_id: Tenant.
            resource_id: ID opcional.

        Returns:
            ID core_resources.

        Raises:
            NotFoundError: Se resource informado não existir.
        """
        if resource_id is not None:
            return self.scheduling_query.get_resource(
                resource_id, company_id
            ).id
        defaults = self.scheduling_query.list_resources(
            company_id, active_only=True
        )
        if not defaults:
            raise NotFoundError("Resource", "default")
        return defaults[0].id

    def _resolve_worker_id(
        self, company_id: int, worker_id: Optional[int]
    ) -> Optional[int]:
        """
        Resolve worker_id informado ou primeiro ativo.

        Args:
            company_id: Tenant.
            worker_id: ID opcional.

        Returns:
            ID core_workers ou None.
        """
        if worker_id is not None:
            return self.scheduling_query.get_worker(worker_id, company_id).id
        workers = self.scheduling_query.list_workers(company_id, active_only=True)
        return workers[0].id if workers else None

    def _get_catalog(self, catalog_id: int, company_id: int) -> CoreCatalog:
        """Carrega catalog com escopo de tenant."""
        catalog = (
            self.db.query(CoreCatalog)
            .filter(
                CoreCatalog.id == catalog_id,
                CoreCatalog.company_id == company_id,
                CoreCatalog.deleted_at.is_(None),
            )
            .first()
        )
        if not catalog:
            raise NotFoundError("Catalog", str(catalog_id))
        if not catalog.active:
            raise BusinessRuleError("Catálogo não está ativo")
        return catalog

    def _get_offering(
        self, offering_id: int, company_id: int, catalog_id: int
    ) -> CoreOffering:
        """Carrega offering com escopo de tenant."""
        offering = (
            self.db.query(CoreOffering)
            .filter(
                CoreOffering.id == offering_id,
                CoreOffering.company_id == company_id,
                CoreOffering.deleted_at.is_(None),
            )
            .first()
        )
        if not offering:
            raise NotFoundError("Offering", str(offering_id))
        if offering.catalog_id != catalog_id:
            raise BusinessRuleError("Offering não pertence ao catalog informado")
        if not offering.active:
            raise BusinessRuleError("Offering não está ativo")
        return offering
