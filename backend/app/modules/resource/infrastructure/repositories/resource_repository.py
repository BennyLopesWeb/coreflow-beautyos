"""
SQLAlchemy adapter — ResourceRepository sobre core_resources (R2-F3).
"""
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.resource.domain.entities.resource import Resource
from app.modules.resource.domain.value_objects.resource_types import (
    Capacity,
    ResourceTypeId,
)
from app.modules.scheduling.domain.models import CoreResource, ResourceType
from app.modules.scheduling.engine.resource_conflict import ResourceConflictService


def _slugify(name: str, entity_id: Optional[int] = None) -> str:
    """
    Gera slug URL-safe.

    Args:
        name: Nome fonte.
        entity_id: Sufixo opcional.

    Returns:
        Slug normalizado.
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "resource").lower()).strip("-")
    if entity_id is not None:
        return f"{base}-{entity_id}"[:120]
    return base[:120]


class SqlAlchemyResourceRepository:
    """
    Persiste aggregate Resource em ``core_resources``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db

    def _to_orm_type(self, type_id: str) -> ResourceType:
        """
        Mapeia string type → enum ORM.

        Args:
            type_id: Tipo canônico.

        Returns:
            ResourceType enum (fallback GENERIC).
        """
        key = (type_id or "generic").upper()
        try:
            return ResourceType[key]
        except KeyError:
            for member in ResourceType:
                if member.value == type_id.lower():
                    return member
            return ResourceType.GENERIC

    def _to_domain(self, row: CoreResource) -> Resource:
        """
        ORM → aggregate.

        Args:
            row: CoreResource.

        Returns:
            Resource domain.
        """
        type_val = (
            row.resource_type.value
            if hasattr(row.resource_type, "value")
            else str(row.resource_type)
        )
        return Resource(
            id=row.id,
            company_id=row.company_id,
            location_id=row.location_id,
            name=row.name,
            slug=row.slug,
            resource_type=ResourceTypeId(type_val),
            capacity=Capacity(row.capacity or 1),
            active=bool(row.active),
            is_default=bool(row.is_default),
            plugin_metadata=row.plugin_metadata or {},
        )

    def _apply(self, row: CoreResource, resource: Resource) -> None:
        """
        Aplica campos do aggregate na linha ORM.

        Args:
            row: Linha alvo.
            resource: Aggregate fonte.
        """
        row.company_id = resource.company_id
        row.location_id = resource.location_id
        row.name = resource.name
        row.slug = resource.slug
        row.resource_type = self._to_orm_type(resource.resource_type.value)
        row.capacity = resource.capacity.value
        row.active = resource.active
        row.is_default = resource.is_default
        row.plugin_metadata = resource.plugin_metadata or {}
        if not resource.active:
            from datetime import datetime, timezone

            row.deleted_at = row.deleted_at or datetime.now(timezone.utc)

    def save(self, resource: Resource) -> Resource:
        """
        Persiste aggregate (insert/update).

        Args:
            resource: Aggregate.

        Returns:
            Aggregate com id.
        """
        if resource.id is None:
            row = CoreResource()
            self._apply(row, resource)
            if not row.slug:
                row.slug = _slugify(resource.name)
            self._db.add(row)
            self._db.flush()
            resource.id = row.id
            if resource.slug.endswith("-0") or resource.slug == _slugify(resource.name):
                resource.slug = _slugify(resource.name, resource.id)
                row.slug = resource.slug
                self._db.flush()
            return resource

        row = (
            self._db.query(CoreResource)
            .filter(
                CoreResource.id == resource.id,
                CoreResource.company_id == resource.company_id,
            )
            .first()
        )
        if not row:
            row = CoreResource(id=resource.id)
            self._db.add(row)
        self._apply(row, resource)
        self._db.flush()
        return resource

    def get_by_id(self, resource_id: int, company_id: int) -> Optional[Resource]:
        """
        Carrega por id + tenant.

        Args:
            resource_id: ID.
            company_id: Tenant.

        Returns:
            Resource ou None.
        """
        row = (
            self._db.query(CoreResource)
            .filter(
                CoreResource.id == resource_id,
                CoreResource.company_id == company_id,
            )
            .first()
        )
        if not row:
            return None
        return self._to_domain(row)

    def list_active(
        self, company_id: int, location_id: Optional[int] = None
    ) -> List[Resource]:
        """
        Lista ativos do tenant.

        Args:
            company_id: Tenant.
            location_id: Filtro opcional.

        Returns:
            Lista de Resource.
        """
        query = self._db.query(CoreResource).filter(
            CoreResource.company_id == company_id,
            CoreResource.active.is_(True),
            CoreResource.deleted_at.is_(None),
        )
        if location_id is not None:
            query = query.filter(CoreResource.location_id == location_id)
        rows = query.order_by(CoreResource.id.asc()).all()
        return [self._to_domain(r) for r in rows]

    def check_availability(
        self,
        company_id: int,
        resource_id: int,
        starts_at,
        ends_at,
    ) -> bool:
        """
        Verifica disponibilidade via ResourceConflictService.

        Args:
            company_id: Tenant.
            resource_id: ID core_resources.
            starts_at: Início.
            ends_at: Fim.

        Returns:
            True se livre.
        """
        resource = self.get_by_id(resource_id, company_id)
        if not resource or not resource.active:
            return False
        conflicts = ResourceConflictService(self._db)
        return not conflicts.has_conflict(
            resource_id=resource_id,
            company_id=company_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
