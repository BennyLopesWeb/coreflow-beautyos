"""
Scheduling Engine — motor genérico de disponibilidade e conflitos.

Não conhece domínio (beauty/sports). Opera sobre Resource, capacity e ScheduleBlock,
com adapter legado opcional (Strangler Fig).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.scheduling.engine.legacy_adapter import (
    LegacySchedulingAdapter,
    merge_occupied_sets,
    slot_fits_duration,
)
from app.modules.scheduling.engine.resource_conflict import (
    SLOT_MINUTES,
    ResourceConflictService,
)
from app.services.agenda_dia_service import AgendaDiaService


@dataclass
class EngineSlot:
    """
    Slot calculado pelo engine genérico.

    Attributes:
        starts_at: Início do slot.
        available: Livre para reserva.
        resource_id: Recurso consultado.
        duration_minutes: Duração considerada.
    """

    starts_at: datetime
    available: bool
    resource_id: int
    duration_minutes: int


@dataclass
class ConflictResult:
    """
    Resultado de verificação de conflito.

    Attributes:
        has_conflict: Se há sobreposição acima da capacity.
        resource_id: Recurso verificado.
        capacity: Capacidade do recurso.
    """

    has_conflict: bool
    resource_id: int
    capacity: int


class SchedulingEngine:
    """
    Motor de scheduling CoreFlow — availability + conflict detection.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.conflicts = ResourceConflictService(db)
        self.agenda = AgendaDiaService(db)
        self.legacy = LegacySchedulingAdapter(db)

    def check_availability(
        self,
        company_id: int,
        resource_id: int,
        target_date: datetime,
        duration_minutes: int,
        legacy_tranca_id: Optional[int] = None,
        legacy_service_image_id: Optional[int] = None,
        merge_legacy: bool = True,
    ) -> List[EngineSlot]:
        """
        Calcula slots disponíveis para um resource em uma data.

        Combina ocupação de ``core_schedule_blocks`` com legado (união) quando
        ``merge_legacy=True`` e IDs legados informados.

        Args:
            company_id: Tenant.
            resource_id: Recurso alvo.
            target_date: Data base (usa expediente do dia).
            duration_minutes: Duração do serviço em minutos.
            legacy_tranca_id: ID tranca (adapter Strangler).
            legacy_service_image_id: ID modelo legado.
            merge_legacy: Unir ocupação legado + core blocks.

        Returns:
            Lista de EngineSlot a cada 30 min.

        Raises:
            NotFoundError: Resource inválido.
        """
        resource = self.conflicts.get_resource(resource_id, company_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        duration = max(duration_minutes or SLOT_MINUTES, SLOT_MINUTES)
        data_date = target_date.date()
        hi, mi, hf, mf, ativo = self.agenda.obter_ou_padrao(data_date)
        if not ativo:
            return []

        window_start = target_date.replace(hour=hi, minute=mi, second=0, microsecond=0)
        window_end = target_date.replace(hour=hf, minute=mf, second=0, microsecond=0)
        capacity = max(resource.capacity or 1, 1)

        core_occupied = self.conflicts.occupied_slot_starts(
            resource_id, company_id, window_start, window_end, capacity
        )

        occupied = core_occupied
        if merge_legacy and legacy_tranca_id is not None:
            legacy_occupied = self.legacy.occupied_slot_starts(
                window_start,
                window_end,
                legacy_tranca_id,
                legacy_service_image_id,
            )
            occupied = merge_occupied_sets(core_occupied, legacy_occupied)

        slots: List[EngineSlot] = []
        now = datetime.now()
        current = window_start
        while current < window_end:
            if current < now:
                available = False
            else:
                available = slot_fits_duration(
                    current, duration, occupied, window_end
                )
            slots.append(
                EngineSlot(
                    starts_at=current,
                    available=available,
                    resource_id=resource_id,
                    duration_minutes=duration,
                )
            )
            current += timedelta(minutes=SLOT_MINUTES)
        return slots

    def detect_conflict(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        ends_at: datetime,
        exclude_block_id: Optional[int] = None,
    ) -> ConflictResult:
        """
        Detecta conflito de alocação em resource (core blocks).

        Args:
            company_id: Tenant.
            resource_id: Recurso.
            starts_at: Início proposto.
            ends_at: Fim proposto.
            exclude_block_id: Bloco ignorado.

        Returns:
            ConflictResult com flag e capacity.

        Raises:
            NotFoundError: Resource inválido.
        """
        resource = self.conflicts.get_resource(resource_id, company_id)
        if not resource:
            raise NotFoundError("Resource", str(resource_id))

        has = self.conflicts.has_conflict(
            resource_id,
            company_id,
            starts_at,
            ends_at,
            exclude_block_id=exclude_block_id,
        )
        return ConflictResult(
            has_conflict=has,
            resource_id=resource_id,
            capacity=max(resource.capacity or 1, 1),
        )

    def validate_booking_window(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        duration_minutes: int,
    ) -> None:
        """
        Valida se janela proposta está livre; lança exceção se conflito.

        Args:
            company_id: Tenant.
            resource_id: Recurso.
            starts_at: Início.
            duration_minutes: Duração.

        Raises:
            BusinessRuleError: Se houver conflito.
            NotFoundError: Resource inválido.
        """
        ends_at = starts_at + timedelta(minutes=max(duration_minutes, SLOT_MINUTES))
        result = self.detect_conflict(company_id, resource_id, starts_at, ends_at)
        if result.has_conflict:
            raise BusinessRuleError("Recurso indisponível no horário solicitado")
