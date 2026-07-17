"""
SqlAlchemyResourceAllocationAdapter — aloca/libera schedule blocks (R2-F3).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.scheduling.domain.models import (
    CoreResource,
    CoreScheduleBlock,
    ScheduleBlockStatus,
)


class SqlAlchemyResourceAllocationAdapter:
    """
    Implementa ResourceAllocationPort via core_schedule_blocks.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db

    def allocate(
        self,
        company_id: int,
        resource_id: int,
        booking_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        """
        Cria schedule block para o booking.

        Args:
            company_id: Tenant.
            resource_id: Resource.
            booking_id: Booking.
            starts_at: Início.
            ends_at: Fim.

        Returns:
            True se criado.
        """
        resource = (
            self._db.query(CoreResource)
            .filter(
                CoreResource.id == resource_id,
                CoreResource.company_id == company_id,
                CoreResource.active.is_(True),
            )
            .first()
        )
        if not resource:
            return False
        block = CoreScheduleBlock(
            company_id=company_id,
            booking_id=booking_id,
            resource_id=resource_id,
            location_id=resource.location_id,
            starts_at=starts_at,
            ends_at=ends_at,
            status=ScheduleBlockStatus.SCHEDULED,
        )
        self._db.add(block)
        self._db.flush()
        return True

    def release(
        self,
        company_id: int,
        resource_id: int,
        booking_id: int,
    ) -> None:
        """
        Cancela schedule blocks do booking.

        Args:
            company_id: Tenant.
            resource_id: Resource.
            booking_id: Booking.

        Returns:
            None
        """
        blocks = (
            self._db.query(CoreScheduleBlock)
            .filter(
                CoreScheduleBlock.company_id == company_id,
                CoreScheduleBlock.resource_id == resource_id,
                CoreScheduleBlock.booking_id == booking_id,
                CoreScheduleBlock.status == ScheduleBlockStatus.SCHEDULED,
            )
            .all()
        )
        for block in blocks:
            block.status = ScheduleBlockStatus.CANCELLED
        self._db.flush()
