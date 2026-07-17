"""
SchedulingResourcePortAdapter — ResourcePort estágio 2 ADR-029 (R2-F3).

Implementa check_availability sobre core_resources (sem tranca_id).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.modules.resource.infrastructure.repositories.resource_repository import (
    SqlAlchemyResourceRepository,
)


class SchedulingResourcePortAdapter:
    """
    Adapter Resource Engine para contrato SchedulingPort (flag ON).

    Usa ``core_resources.id`` — zero ``tranca_id`` (FF-SCH-001).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db
        self._repo = SqlAlchemyResourceRepository(db)

    def check_availability(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        ends_at: datetime,
        worker_id: Optional[int] = None,
        offering_id: Optional[int] = None,
        legacy_tranca_id: Optional[int] = None,
        legacy_service_image_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica disponibilidade via ResourceConflictService.

        Args:
            company_id: Tenant.
            resource_id: ID core_resources (não catalog_id).
            starts_at: Início.
            ends_at: Fim.
            worker_id: Ignorado F3.
            offering_id: Ignorado F3.
            legacy_tranca_id: Ignorado no path Resource Engine (FF-SCH-001).
            legacy_service_image_id: Ignorado no path Resource Engine.

        Returns:
            True se slot livre.
        """
        ArchitectureMetricsStore.get().record_resource_engine_path()
        available = self._repo.check_availability(
            company_id=company_id,
            resource_id=resource_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        if not available:
            ArchitectureMetricsStore.get().record_resource_conflict()
        return available
