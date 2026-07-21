"""
ACL — SchedulingPort adapter (ADR-029 estágio 1 / R2-F1).

Encapsula disponibilidade legado com paridade ``ReservationService.criar_de_schema``.

R4-F2 (ADR-024 sunset): com ``booking.legacy.projection.enabled`` OFF por
padrão, bookings core-only não geram mais linha em ``agendamentos`` — logo
``DisponibilidadeService`` (que consulta ``agendamentos``) não vê essas
reservas. ``check_availability`` passa a consultar ``core_bookings``
diretamente para preservar a paridade P02/P09 (slot indisponível /
double-booking).

R4-F3: dual-write outbound removido definitivamente — todo booking é
core-only, então a consulta direta a ``core_bookings`` descrita acima
deixa de ser condicional e passa a ser o único comportamento.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.logging_config import get_logger
from app.models.agendamento import STATUS_OCUPAM_VAGA
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.schedule_service import ScheduleService

logger = get_logger("acl_scheduling")


class LegacySchedulingPortAdapter:
    """
    Implementação ACL de ``SchedulingPort`` para paridade com legado.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db
        self._disponibilidade = DisponibilidadeService(db)
        self._schedule = ScheduleService(db)

    def _track(self) -> None:
        """
        Registra invocação ACL para telemetria.

        Returns:
            None
        """
        ArchitectureMetricsStore.get().record_acl_invocation()

    def _resolve_legacy_tranca_id(
        self, resource_id: int, company_id: int, legacy_tranca_id: Optional[int]
    ) -> int:
        """
        Resolve tranca legado a partir de catalog id ou parâmetro explícito.

        Args:
            resource_id: catalog_id interim.
            company_id: Tenant.
            legacy_tranca_id: Override quando já resolvido.

        Returns:
            legacy_tranca_id.

        Raises:
            ValueError: Sem mapeamento.
        """
        if legacy_tranca_id is not None:
            return legacy_tranca_id
        catalog = (
            self._db.query(CoreCatalog)
            .filter(
                CoreCatalog.id == resource_id,
                CoreCatalog.company_id == company_id,
            )
            .first()
        )
        if not catalog or not catalog.legacy_tranca_id:
            raise ValueError(f"Resource/catalog {resource_id} sem mapeamento legado")
        return catalog.legacy_tranca_id

    def _resolve_duration_minutes(self, offering_id: Optional[int], company_id: int) -> int:
        """
        Resolve duração (min) de um ``core_offering`` para overlap de slot.

        Args:
            offering_id: ID core_offerings; None usa fallback.
            company_id: Tenant.

        Returns:
            Duração em minutos (default 30 se offering ausente/sem duração).
        """
        if offering_id is None:
            return 30
        offering = (
            self._db.query(CoreOffering)
            .filter(
                CoreOffering.id == offering_id,
                CoreOffering.company_id == company_id,
            )
            .first()
        )
        if offering and offering.duration_minutes:
            return max(int(offering.duration_minutes), 1)
        return 30

    def _has_core_booking_conflict(
        self,
        company_id: int,
        resource_id: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> bool:
        """
        Verifica conflito com ``core_bookings`` ativos no mesmo catalog (R4-F2).

        Necessário porque bookings core-only (projeção legado OFF) não
        aparecem em ``agendamentos`` — sem esta checagem, dois creates no
        mesmo slot seriam ambos aceitos (quebra P02/P09).

        Args:
            company_id: Tenant.
            resource_id: catalog_id interim (mesma convenção do restante do port).
            starts_at: Início do slot candidato.
            ends_at: Fim do slot candidato.

        Returns:
            True se houver overlap com booking ativo (não cancelled/rejected/deleted).
        """
        from app.modules.booking.domain.models import CoreBooking

        s = starts_at.replace(tzinfo=None) if starts_at.tzinfo else starts_at
        e = ends_at.replace(tzinfo=None) if ends_at.tzinfo else ends_at

        rows = (
            self._db.query(CoreBooking)
            .filter(
                CoreBooking.company_id == company_id,
                CoreBooking.catalog_id == resource_id,
                CoreBooking.deleted_at.is_(None),
                CoreBooking.status.in_(STATUS_OCUPAM_VAGA),
            )
            .all()
        )
        for row in rows:
            duration = self._resolve_duration_minutes(row.offering_id, company_id)
            row_start = (
                row.scheduled_at.replace(tzinfo=None)
                if row.scheduled_at.tzinfo
                else row.scheduled_at
            )
            row_end = row_start + timedelta(minutes=duration)
            if row_start < e and row_end > s:
                return True
        return False

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
        Verifica disponibilidade com mesmas regras do ``ReservationService``.

        Combina três checagens independentes (todas devem passar): slot
        dentro do expediente e livre em ``agendamentos`` (legado), sem
        conflito em ``schedules`` (bloqueios pós-approve) e sem overlap em
        ``core_bookings`` ativos (R4-F2 — cobre bookings core-only sem
        projeção legado).

        Args:
            company_id: Tenant.
            resource_id: catalog_id interim.
            starts_at: Início candidato.
            ends_at: Fim candidato.
            worker_id: Ignorado estágio 1.
            offering_id: Offering core (resolve legacy image se necessário).
            legacy_tranca_id: ID tranca legado.
            legacy_service_image_id: ID service image legado.

        Returns:
            True se slot disponível e sem conflito na agenda.
        """
        self._track()
        tranca_id = self._resolve_legacy_tranca_id(
            resource_id, company_id, legacy_tranca_id
        )

        service_image_id = legacy_service_image_id
        if service_image_id is None and offering_id is not None:
            offering = (
                self._db.query(CoreOffering)
                .filter(CoreOffering.id == offering_id)
                .first()
            )
            if offering:
                service_image_id = offering.legacy_service_image_id

        horarios = self._disponibilidade.calcular_horarios_disponiveis(
            starts_at, tranca_id, service_image_id
        )
        slot_ok = any(
            h.horario.replace(tzinfo=None) == starts_at.replace(tzinfo=None)
            and h.disponivel
            for h in horarios
        )
        if not slot_ok:
            logger.debug("[acl] slot not in horarios disponiveis tranca=%s", tranca_id)
            return False

        if self._schedule.tem_conflito(starts_at, ends_at):
            logger.debug("[acl] schedule conflict")
            return False

        if self._has_core_booking_conflict(company_id, resource_id, starts_at, ends_at):
            logger.debug("[acl] core_bookings conflict resource=%s", resource_id)
            return False

        return True
