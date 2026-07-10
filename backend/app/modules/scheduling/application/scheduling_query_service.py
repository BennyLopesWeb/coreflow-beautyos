"""
Consultas read-only do metamodelo scheduling CoreFlow.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.scheduling.domain.models import CoreLocation, CoreResource, CoreWorker


class SchedulingQueryService:
    """
    Serviço de leitura para Location, Worker e Resource.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_locations(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreLocation]:
        """
        Lista unidades físicas do tenant.

        Args:
            company_id: ID da empresa.
            active_only: Filtra apenas ativos.

        Returns:
            Lista de CoreLocation.
        """
        query = self.db.query(CoreLocation).filter(
            CoreLocation.company_id == company_id,
            CoreLocation.deleted_at.is_(None),
        )
        if active_only:
            query = query.filter(CoreLocation.active.is_(True))
        return query.order_by(CoreLocation.is_default.desc(), CoreLocation.name).all()

    def get_location(self, location_id: int, company_id: int) -> CoreLocation:
        """
        Obtém unidade por ID com escopo de tenant.

        Args:
            location_id: ID core_locations.
            company_id: ID da empresa.

        Returns:
            CoreLocation encontrado.

        Raises:
            NotFoundError: Se não existir ou não pertencer ao tenant.
        """
        row = (
            self.db.query(CoreLocation)
            .filter(
                CoreLocation.id == location_id,
                CoreLocation.company_id == company_id,
                CoreLocation.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Location", str(location_id))
        return row

    def list_workers(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreWorker]:
        """
        Lista profissionais do tenant.

        Args:
            company_id: ID da empresa.
            active_only: Filtra apenas ativos.

        Returns:
            Lista de CoreWorker.
        """
        query = self.db.query(CoreWorker).filter(
            CoreWorker.company_id == company_id,
            CoreWorker.deleted_at.is_(None),
        )
        if active_only:
            query = query.filter(CoreWorker.active.is_(True))
        return query.order_by(CoreWorker.display_name).all()

    def get_worker(self, worker_id: int, company_id: int) -> CoreWorker:
        """
        Obtém profissional por ID com escopo de tenant.

        Args:
            worker_id: ID core_workers.
            company_id: ID da empresa.

        Returns:
            CoreWorker encontrado.

        Raises:
            NotFoundError: Se não existir ou não pertencer ao tenant.
        """
        row = (
            self.db.query(CoreWorker)
            .filter(
                CoreWorker.id == worker_id,
                CoreWorker.company_id == company_id,
                CoreWorker.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Worker", str(worker_id))
        return row

    def list_resources(
        self,
        company_id: int,
        location_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[CoreResource]:
        """
        Lista recursos reserváveis do tenant.

        Args:
            company_id: ID da empresa.
            location_id: Filtra por unidade (opcional).
            active_only: Filtra apenas ativos.

        Returns:
            Lista de CoreResource.
        """
        query = self.db.query(CoreResource).filter(
            CoreResource.company_id == company_id,
            CoreResource.deleted_at.is_(None),
        )
        if location_id is not None:
            query = query.filter(CoreResource.location_id == location_id)
        if active_only:
            query = query.filter(CoreResource.active.is_(True))
        return query.order_by(CoreResource.is_default.desc(), CoreResource.name).all()

    def get_resource(self, resource_id: int, company_id: int) -> CoreResource:
        """
        Obtém recurso por ID com escopo de tenant.

        Args:
            resource_id: ID core_resources.
            company_id: ID da empresa.

        Returns:
            CoreResource encontrado.

        Raises:
            NotFoundError: Se não existir ou não pertencer ao tenant.
        """
        row = (
            self.db.query(CoreResource)
            .filter(
                CoreResource.id == resource_id,
                CoreResource.company_id == company_id,
                CoreResource.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Resource", str(resource_id))
        return row
