"""
Sincronização Strangler Fig — legado → metamodelo scheduling CoreFlow.

Garante Location/Resource/Worker padrão por tenant e espelha ``schedules``.
"""
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.company import Company
from app.models.schedule import Schedule, ScheduleStatus
from app.models.user import User
from app.models.user_company import ADMIN_ROLES, UserCompany
from app.modules.booking.domain.models import CoreBooking
from app.modules.scheduling.domain.models import (
    CoreLocation,
    CoreResource,
    CoreScheduleBlock,
    CoreWorker,
    ResourceType,
    ScheduleBlockStatus,
)

logger = get_logger("scheduling_sync")

_STATUS_MAP = {
    ScheduleStatus.SCHEDULED: ScheduleBlockStatus.SCHEDULED,
    ScheduleStatus.BLOCKED: ScheduleBlockStatus.BLOCKED,
    ScheduleStatus.COMPLETED: ScheduleBlockStatus.COMPLETED,
    ScheduleStatus.CANCELLED: ScheduleBlockStatus.CANCELLED,
}


def _slugify(name: str, entity_id: int) -> str:
    """
    Gera slug URL-safe a partir do nome.

    Args:
        name: Nome da entidade.
        entity_id: ID para desambiguação.

    Returns:
        Slug normalizado.
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "item").lower()).strip("-")
    return f"{base}-{entity_id}"[:120]


class SchedulingLegacySyncService:
    """
    Sincroniza entidades legadas e defaults para o metamodelo de scheduling.

    Idempotente — pode rodar no startup e após migrações.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> dict:
        """
        Executa sync completo location → resource → worker → schedule_block.

        Returns:
            Dict com contagens por entidade.
        """
        locations = self.sync_locations()
        resources = self.sync_resources()
        workers = self.sync_workers()
        blocks = self.sync_schedule_blocks()
        return {
            "locations": locations,
            "resources": resources,
            "workers": workers,
            "schedule_blocks": blocks,
        }

    def sync_locations(self) -> int:
        """
        Garante um ``core_locations`` padrão por empresa ativa.

        Returns:
            Quantidade processada.
        """
        companies = self.db.query(Company).filter(Company.deleted_at.is_(None)).all()
        count = 0
        for company in companies:
            existing = (
                self.db.query(CoreLocation)
                .filter(
                    CoreLocation.company_id == company.id,
                    CoreLocation.is_default.is_(True),
                    CoreLocation.deleted_at.is_(None),
                )
                .first()
            )
            slug = _slugify(company.slug or company.nome, company.id)
            payload = dict(
                company_id=company.id,
                name=company.nome,
                slug=slug,
                address={},
                timezone=company.timezone,
                active=company.ativo,
                is_default=True,
                plugin_metadata={"source": "beauty", "legacy": "implicit_single_location"},
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(CoreLocation(**payload))
            count += 1
        self.db.commit()
        logger.info(f"Sync locations: {count}")
        return count

    def sync_resources(self) -> int:
        """
        Garante recurso padrão (cadeira, capacidade 1) por local.

        Returns:
            Quantidade processada.
        """
        locations = (
            self.db.query(CoreLocation)
            .filter(CoreLocation.deleted_at.is_(None))
            .all()
        )
        count = 0
        for location in locations:
            existing = (
                self.db.query(CoreResource)
                .filter(
                    CoreResource.location_id == location.id,
                    CoreResource.is_default.is_(True),
                    CoreResource.deleted_at.is_(None),
                )
                .first()
            )
            slug = _slugify("principal", location.id)
            payload = dict(
                company_id=location.company_id,
                location_id=location.id,
                name="Atendimento principal",
                slug=slug,
                resource_type=ResourceType.CHAIR,
                capacity=1,
                active=True,
                is_default=True,
                plugin_metadata={"source": "beauty", "legacy": "implicit_single_chair"},
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(CoreResource(**payload))
            count += 1
        self.db.commit()
        logger.info(f"Sync resources: {count}")
        return count

    def sync_workers(self) -> int:
        """
        Sincroniza usuários owner/professional → ``core_workers``.

        Returns:
            Quantidade processada.
        """
        memberships = (
            self.db.query(UserCompany)
            .filter(UserCompany.role.in_(tuple(ADMIN_ROLES)))
            .all()
        )
        count = 0
        for membership in memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if not user or user.deleted_at is not None:
                continue

            existing = (
                self.db.query(CoreWorker)
                .filter(
                    CoreWorker.company_id == membership.company_id,
                    CoreWorker.user_id == user.id,
                    CoreWorker.deleted_at.is_(None),
                )
                .first()
            )
            role_value = (
                membership.role.value
                if hasattr(membership.role, "value")
                else str(membership.role)
            )
            payload = dict(
                company_id=membership.company_id,
                user_id=user.id,
                display_name=user.nome,
                email=user.email,
                role=role_value,
                active=user.ativo,
                plugin_metadata={"source": "beauty", "legacy": "UserCompany"},
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(CoreWorker(**payload))
            count += 1
        self.db.commit()
        logger.info(f"Sync workers: {count}")
        return count

    def sync_schedule_blocks(self) -> int:
        """
        Sincroniza ``schedules`` → ``core_schedule_blocks``.

        Returns:
            Quantidade processada.
        """
        schedules = self.db.query(Schedule).all()
        count = 0
        for schedule in schedules:
            booking = (
                self.db.query(CoreBooking)
                .filter(CoreBooking.legacy_agendamento_id == schedule.agendamento_id)
                .first()
            )
            if not booking:
                continue

            company_id = schedule.company_id or booking.company_id
            location = self._default_location(company_id)
            resource = self._default_resource(company_id)
            if not location or not resource:
                continue

            existing = (
                self.db.query(CoreScheduleBlock)
                .filter(CoreScheduleBlock.legacy_schedule_id == schedule.id)
                .first()
            )
            status = _STATUS_MAP.get(schedule.status, ScheduleBlockStatus.SCHEDULED)
            payload = dict(
                company_id=company_id,
                booking_id=booking.id,
                resource_id=resource.id,
                worker_id=self._default_worker_id(company_id),
                location_id=location.id,
                starts_at=schedule.inicio,
                ends_at=schedule.fim,
                status=status,
            )
            if existing:
                for key, val in payload.items():
                    setattr(existing, key, val)
            else:
                self.db.add(
                    CoreScheduleBlock(legacy_schedule_id=schedule.id, **payload)
                )
            count += 1
        self.db.commit()
        logger.info(f"Sync schedule_blocks: {count}")
        return count

    def _default_location(self, company_id: int) -> Optional[CoreLocation]:
        """
        Retorna local padrão do tenant.

        Args:
            company_id: ID da empresa.

        Returns:
            CoreLocation ou None.
        """
        return (
            self.db.query(CoreLocation)
            .filter(
                CoreLocation.company_id == company_id,
                CoreLocation.is_default.is_(True),
                CoreLocation.deleted_at.is_(None),
            )
            .first()
        )

    def _default_resource(self, company_id: int) -> Optional[CoreResource]:
        """
        Retorna recurso padrão do tenant.

        Args:
            company_id: ID da empresa.

        Returns:
            CoreResource ou None.
        """
        return (
            self.db.query(CoreResource)
            .filter(
                CoreResource.company_id == company_id,
                CoreResource.is_default.is_(True),
                CoreResource.deleted_at.is_(None),
            )
            .first()
        )

    def _default_worker_id(self, company_id: int) -> Optional[int]:
        """
        Retorna ID do worker owner/professional padrão.

        Args:
            company_id: ID da empresa.

        Returns:
            ID core_workers ou None.
        """
        worker = (
            self.db.query(CoreWorker)
            .filter(
                CoreWorker.company_id == company_id,
                CoreWorker.active.is_(True),
                CoreWorker.deleted_at.is_(None),
            )
            .order_by(CoreWorker.id.asc())
            .first()
        )
        return worker.id if worker else None
