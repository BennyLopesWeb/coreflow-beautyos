"""
ACL — SchedulingPort adapter (ADR-029 estágio 1 / R2-F1).

Encapsula disponibilidade legado com paridade ``ReservationService.criar_de_schema``.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.logging_config import get_logger
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

        return True
