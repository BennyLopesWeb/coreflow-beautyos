"""
Adapter legado — traduz Agendamento/disponibilidade para o scheduling engine.

Strangler Fig: mantém paridade com regras existentes enquanto ``core_schedule_blocks``
é populado progressivamente.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.schemas.agendamento import HorarioDisponivel
from app.services.disponibilidade_service import DisponibilidadeService

from app.modules.scheduling.engine.resource_conflict import SLOT_MINUTES


class LegacySchedulingAdapter:
    """
    Adapta ``DisponibilidadeService`` para vocabulário genérico de slots.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.disponibilidade = DisponibilidadeService(db)

    def occupied_slot_starts(
        self,
        window_start: datetime,
        window_end: datetime,
        legacy_tranca_id: int,
        legacy_service_image_id: Optional[int] = None,
    ) -> Set[datetime]:
        """
        Deriva slots ocupados via agendamentos legados (capacidade única implícita).

        Args:
            window_start: Início do expediente.
            window_end: Fim do expediente.
            legacy_tranca_id: ID tranca.
            legacy_service_image_id: ID service_image (duração).

        Returns:
            Set de inícios de slot de 30 min ocupados.
        """
        self.disponibilidade.expirar_reservas_pendentes()

        day = window_start.replace(hour=0, minute=0, second=0, microsecond=0)
        horarios = self.disponibilidade.calcular_horarios_disponiveis(
            day, legacy_tranca_id, legacy_service_image_id
        )
        occupied: Set[datetime] = set()
        for slot in horarios:
            if not slot.disponivel and window_start <= slot.horario < window_end:
                occupied.add(slot.horario.replace(second=0, microsecond=0))
        return occupied

    def calcular_slots(
        self,
        target_date: datetime,
        duration_minutes: int,
        legacy_tranca_id: int,
        legacy_service_image_id: Optional[int] = None,
    ) -> List[HorarioDisponivel]:
        """
        Delega cálculo completo ao serviço legado.

        Args:
            target_date: Data base.
            duration_minutes: Ignorado (legado resolve via service_image).
            legacy_tranca_id: ID tranca.
            legacy_service_image_id: ID modelo.

        Returns:
            Lista HorarioDisponivel legado.
        """
        return self.disponibilidade.calcular_horarios_disponiveis(
            target_date.replace(hour=0, minute=0, second=0, microsecond=0),
            legacy_tranca_id,
            legacy_service_image_id,
        )


def merge_occupied_sets(*sets: Set[datetime]) -> Set[datetime]:
    """
    Une conjuntos de slots ocupados (união).

    Args:
        *sets: Conjuntos de datetime.

    Returns:
        União de todos os conjuntos.
    """
    merged: Set[datetime] = set()
    for s in sets:
        merged |= s
    return merged


def slot_fits_duration(
    start: datetime,
    duration_minutes: int,
    occupied: Set[datetime],
    window_end: datetime,
) -> bool:
    """
    Verifica se todos os slots de 30 min da duração estão livres.

    Args:
        start: Início candidato.
        duration_minutes: Duração total.
        occupied: Slots ocupados.
        window_end: Fim do expediente.

    Returns:
        True se cabe sem conflito.
    """
    for i in range(0, max(duration_minutes, SLOT_MINUTES), SLOT_MINUTES):
        slot = start + timedelta(minutes=i)
        if slot >= window_end:
            return False
        if slot.replace(second=0, microsecond=0) in occupied:
            return False
    return True
