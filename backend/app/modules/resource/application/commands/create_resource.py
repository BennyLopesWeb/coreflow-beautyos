"""
Command CreateResource — CQRS Resource Engine (R2-F3).
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import NotFoundError, ValidationError
from app.core.feature_flags import feature_flags
from app.modules.resource.domain.events import resource_created
from app.modules.resource.domain.exceptions import (
    InvalidResourceCapacityError,
    UnknownResourceTypeError,
)
from app.modules.resource.domain.services.resource_domain_service import (
    ResourceDomainService,
)
from app.modules.resource.infrastructure.adapters.resource_type_adapter import (
    PluginResourceTypeAdapter,
)
from app.modules.resource.infrastructure.repositories.resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.modules.scheduling.domain.models import CoreLocation
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class CreateResourceCommand:
    """
    Comando para criar resource.

    Attributes:
        company_id: Tenant.
        location_id: Unidade.
        name: Nome.
        slug: Slug opcional (gerado se ausente).
        resource_type: Tipo (chair, …).
        capacity: Capacidade.
        is_default: Default do local.
        plugin_id: Plugin para validar tipos.
        correlation_id: Rastreio opcional.
    """

    company_id: int
    location_id: int
    name: str
    resource_type: str
    capacity: int = 1
    is_default: bool = False
    slug: Optional[str] = None
    plugin_id: str = "beauty"
    correlation_id: Optional[str] = None


class CreateResourceHandler:
    """
    Handler CQRS — create resource (flag resource.engine.enabled).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, command: CreateResourceCommand):
        """
        Cria resource + outbox resource.created.

        Args:
            command: Dados validados.

        Returns:
            CoreResource ORM (para serialização API).

        Raises:
            ValidationError: Flag OFF ou dados inválidos.
            NotFoundError: Location inexistente.
        """
        if not feature_flags.is_enabled("resource.engine.enabled"):
            raise ValidationError("resource_engine_disabled")

        location = (
            self.db.query(CoreLocation)
            .filter(
                CoreLocation.id == command.location_id,
                CoreLocation.company_id == command.company_id,
                CoreLocation.deleted_at.is_(None),
            )
            .first()
        )
        if not location:
            raise NotFoundError("Location", str(command.location_id))

        slug = command.slug or f"{command.name}-{command.location_id}"
        type_port = PluginResourceTypeAdapter()
        domain = ResourceDomainService(type_port=type_port)
        repo = SqlAlchemyResourceRepository(self.db)

        try:
            resource = domain.create(
                company_id=command.company_id,
                location_id=command.location_id,
                name=command.name,
                slug=slug,
                resource_type=command.resource_type,
                capacity=command.capacity,
                is_default=command.is_default,
                plugin_id=command.plugin_id,
            )
        except (UnknownResourceTypeError, InvalidResourceCapacityError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

        resource = repo.save(resource)
        outbox = OutboxBatch(self.db)
        outbox.record(
            resource_created(
                company_id=command.company_id,
                resource_id=resource.id,
                location_id=command.location_id,
                capacity=resource.capacity.value,
                resource_type=resource.resource_type.value,
                correlation_id=command.correlation_id,
            )
        )
        self.db.commit()
        outbox.publish_after_commit()
        ArchitectureMetricsStore.get().record_resource_create()

        from app.modules.scheduling.domain.models import CoreResource

        return (
            self.db.query(CoreResource)
            .filter(CoreResource.id == resource.id)
            .first()
        )
