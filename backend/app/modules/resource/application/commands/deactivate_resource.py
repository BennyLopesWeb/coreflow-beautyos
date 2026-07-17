"""
Command DeactivateResource — CQRS Resource Engine (R2-F3).
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.feature_flags import feature_flags
from app.modules.resource.domain.events import resource_updated
from app.modules.resource.domain.services.resource_domain_service import (
    ResourceDomainService,
)
from app.modules.resource.infrastructure.repositories.resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class DeactivateResourceCommand:
    """
    Comando para soft-deactivate resource.

    Attributes:
        company_id: Tenant.
        resource_id: ID.
        correlation_id: Rastreio opcional.
    """

    company_id: int
    resource_id: int
    correlation_id: Optional[str] = None


class DeactivateResourceHandler:
    """
    Handler CQRS — deactivate resource.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, command: DeactivateResourceCommand):
        """
        Desativa resource (idempotente).

        Args:
            command: Dados.

        Returns:
            CoreResource ORM.

        Raises:
            ValidationError: Flag OFF.
            NotFoundError: Resource ausente.
        """
        if not feature_flags.is_enabled("resource.engine.enabled"):
            raise ValidationError("resource_engine_disabled")

        repo = SqlAlchemyResourceRepository(self.db)
        resource = repo.get_by_id(command.resource_id, command.company_id)
        if not resource:
            raise NotFoundError("Resource", str(command.resource_id))

        domain = ResourceDomainService()
        resource = domain.deactivate(resource)
        resource = repo.save(resource)
        outbox = OutboxBatch(self.db)
        outbox.record(
            resource_updated(
                company_id=command.company_id,
                resource_id=resource.id,
                changes={"active": False},
                correlation_id=command.correlation_id,
            )
        )
        self.db.commit()
        outbox.publish_after_commit()

        from app.modules.scheduling.domain.models import CoreResource

        return (
            self.db.query(CoreResource)
            .filter(CoreResource.id == resource.id)
            .first()
        )
