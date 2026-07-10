"""
Detecção de conflitos por Resource — Resource Engine (CoreFlow).

O scheduling engine não conhece o domínio (beauty/sports); apenas reserva Resources
e verifica sobreposição temporal respeitando ``capacity``.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.modules.scheduling.domain.models import (
    CoreResource,
    CoreScheduleBlock,
    ScheduleBlockStatus,
)

SLOT_MINUTES = 30

OCCUPYING_BLOCK_STATUSES = frozenset(
    {
        ScheduleBlockStatus.SCHEDULED,
        ScheduleBlockStatus.BLOCKED,
    }
)


@dataclass(frozen=True)
class TimeInterval:
    """
    Intervalo temporal semi-aberto [starts_at, ends_at).

    Attributes:
        starts_at: Início inclusivo.
        ends_at: Fim exclusivo.
    """

    starts_at: datetime
    ends_at: datetime

    def overlaps(self, other: "TimeInterval") -> bool:
        """
        Verifica sobreposição com outro intervalo.

        Args:
            other: Intervalo comparado.

        Returns:
            True se houver interseção.
        """
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at


class ResourceConflictService:
    """
    Detecta conflitos de alocação em ``core_schedule_blocks`` por resource.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_resource(self, resource_id: int, company_id: int) -> Optional[CoreResource]:
        """
        Carrega recurso com escopo de tenant.

        Args:
            resource_id: ID core_resources.
            company_id: ID da empresa.

        Returns:
            CoreResource ou None.
        """
        return (
            self.db.query(CoreResource)
            .filter(
                CoreResource.id == resource_id,
                CoreResource.company_id == company_id,
                CoreResource.deleted_at.is_(None),
                CoreResource.active.is_(True),
            )
            .first()
        )

    def list_blocks_in_window(
        self,
        resource_id: int,
        company_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> List[CoreScheduleBlock]:
        """
        Lista blocos ativos do recurso que intersectam a janela.

        Args:
            resource_id: Recurso consultado.
            company_id: Tenant.
            window_start: Início da janela.
            window_end: Fim da janela.

        Returns:
            Lista de CoreScheduleBlock ordenada por starts_at.
        """
        return (
            self.db.query(CoreScheduleBlock)
            .filter(
                CoreScheduleBlock.resource_id == resource_id,
                CoreScheduleBlock.company_id == company_id,
                CoreScheduleBlock.deleted_at.is_(None),
                CoreScheduleBlock.status.in_(tuple(OCCUPYING_BLOCK_STATUSES)),
                CoreScheduleBlock.starts_at < window_end,
                CoreScheduleBlock.ends_at > window_start,
            )
            .order_by(CoreScheduleBlock.starts_at.asc())
            .all()
        )

    def occupied_slot_starts(
        self,
        resource_id: int,
        company_id: int,
        window_start: datetime,
        window_end: datetime,
        capacity: int = 1,
    ) -> Set[datetime]:
        """
        Calcula inícios de slots de 30 min onde capacidade está esgotada.

        Para capacity=1, qualquer bloco sobreposto ocupa o slot.
        Para capacity>1, conta blocos simultâneos por slot.

        Args:
            resource_id: Recurso consultado.
            company_id: Tenant.
            window_start: Início do expediente.
            window_end: Fim do expediente.
            capacity: Vagas simultâneas do recurso.

        Returns:
            Set de datetimes (início de slot) totalmente ocupados.
        """
        blocks = self.list_blocks_in_window(
            resource_id, company_id, window_start, window_end
        )
        intervals = [
            TimeInterval(starts_at=b.starts_at, ends_at=b.ends_at) for b in blocks
        ]

        occupied: Set[datetime] = set()
        current = window_start.replace(second=0, microsecond=0)
        while current < window_end:
            slot_end = current + timedelta(minutes=SLOT_MINUTES)
            concurrent = sum(
                1
                for iv in intervals
                if iv.overlaps(TimeInterval(starts_at=current, ends_at=slot_end))
            )
            if concurrent >= max(capacity, 1):
                occupied.add(current)
            current += timedelta(minutes=SLOT_MINUTES)
        return occupied

    def has_conflict(
        self,
        resource_id: int,
        company_id: int,
        starts_at: datetime,
        ends_at: datetime,
        exclude_block_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica se intervalo proposto conflita com blocos existentes (cap=1).

        Args:
            resource_id: Recurso alvo.
            company_id: Tenant.
            starts_at: Início proposto.
            ends_at: Fim proposto.
            exclude_block_id: Bloco ignorado (reagendamento).

        Returns:
            True se houver conflito.
        """
        resource = self.get_resource(resource_id, company_id)
        if not resource:
            return True

        capacity = max(resource.capacity or 1, 1)
        proposed = TimeInterval(starts_at=starts_at, ends_at=ends_at)

        blocks = self.list_blocks_in_window(
            resource_id, company_id, starts_at, ends_at
        )
        overlapping = 0
        for block in blocks:
            if exclude_block_id and block.id == exclude_block_id:
                continue
            interval = TimeInterval(starts_at=block.starts_at, ends_at=block.ends_at)
            if proposed.overlaps(interval):
                overlapping += 1
                if overlapping >= capacity:
                    return True
        return False
