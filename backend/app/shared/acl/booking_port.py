"""
ACL — Anti-Corruption Layer entre Core e Legado (RFC-002 / R1-F2).

Ports definem contratos core; adapters encapsulam legado.

R3-F2 (ADR-027/ADR-033/RFC-003 M4): os métodos ``*_via_legacy`` **nunca**
delegam mais a ``ReservationService`` — o path de escrita legado foi
removido. Eles apenas registram telemetria ACL, emitem warning e levantam
``BusinessRuleError`` apontando para ``/v1/bookings``. Os métodos
``project_*`` (dual-write outbound), ``resolve_legacy_ids``,
``sync_booking_from_agendamento`` e ``get_booking_legacy_id`` permanecem
inalterados — continuam servindo o path core.
"""
from typing import Any, Dict, Optional, Protocol, Tuple

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import BusinessRuleError
from app.core.logging_config import get_logger

logger = get_logger("acl_booking")


class BookingPort(Protocol):
    """
    Port hexagonal para operações de booking.

    Core modules devem depender desta interface — nunca de ``ReservationService`` direto.

    R3-F2: ``*_via_legacy`` são fail-fast (``BusinessRuleError``) — a escrita
    legada foi removida; apenas ``project_*`` (dual-write outbound) e as
    operações de leitura/sync permanecem funcionais.
    """

    def resolve_legacy_ids(
        self, catalog_id: int, offering_id: int
    ) -> Tuple[int, int]:
        """
        Resolve IDs legado a partir de catalog/offering core.

        Args:
            catalog_id: ID core_catalogs.
            offering_id: ID core_offerings.

        Returns:
            Tupla (tranca_id, service_image_id).
        """
        ...

    def create_booking_via_legacy(
        self,
        customer_id: int,
        tranca_id: int,
        service_image_id: int,
        scheduled_at: Any,
        company_id: int,
        notes: Optional[str] = None,
    ) -> Any:
        """
        Cria reserva via camada legado encapsulada.

        Args:
            customer_id: ID cliente.
            tranca_id: ID tranca legado.
            service_image_id: ID modelo legado.
            scheduled_at: Datetime agendamento.
            company_id: Tenant.
            notes: Observações.

        Returns:
            Agendamento legado criado.

        Raises:
            BusinessRuleError: Sempre — path removido em R3-F2.
        """
        ...

    def approve_booking_via_legacy(self, legacy_agendamento_id: int) -> None:
        """
        Aprova agendamento legado (removido em R3-F2).

        Args:
            legacy_agendamento_id: ID agendamentos.

        Raises:
            BusinessRuleError: Sempre — path removido em R3-F2.
        """
        ...

    def reject_booking_via_legacy(
        self, legacy_agendamento_id: int, reason: str
    ) -> None:
        """
        Rejeita agendamento legado (removido em R3-F2).

        Args:
            legacy_agendamento_id: ID agendamentos.
            reason: Motivo da rejeição.

        Raises:
            BusinessRuleError: Sempre — path removido em R3-F2.
        """
        ...

    def get_booking_legacy_id(self, booking_id: int, company_id: int) -> Optional[int]:
        """
        Resolve ID legado a partir de core booking id.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            legacy agendamento id ou None.
        """
        ...


class LegacyBookingAdapter:
    """
    Adapter ACL — delega ao legado através de fronteira explícita.

    R1-F2: wiring implementado; commands CQRS migram para adapter em Release 2.
    R2: path core nativo em uso via ``project_*`` (dual-write ADR-024/025).
    R3-F2: métodos ``*_via_legacy`` (create/approve/reject/cancel) não
    delegam mais a ``ReservationService`` — sempre levantam
    ``BusinessRuleError`` apontando para ``/v1/bookings`` (ADR-027/ADR-033).
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self._db = db

    def _track(self) -> None:
        """
        Registra invocação ACL para telemetria.

        Returns:
            None
        """
        ArchitectureMetricsStore.get().record_acl_invocation()

    def create_booking_via_legacy(
        self,
        customer_id: int,
        tranca_id: int,
        service_image_id: int,
        scheduled_at: Any,
        company_id: int,
        notes: Optional[str] = None,
    ) -> Any:
        """
        Path legado de criação — **removido em R3-F2**.

        Antes delegava a ``ReservationService.criar_de_schema``; agora
        apenas registra telemetria/log e falha explicitamente, já que o
        booking core-only (ADR-027/ADR-033) é o único caminho de escrita.

        Args:
            customer_id: ID cliente.
            tranca_id: ID tranca.
            service_image_id: ID service image.
            scheduled_at: Horário.
            company_id: Tenant.
            notes: Notas.

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        self._track()
        logger.warning(
            "[acl] create_booking_via_legacy chamado — path legado removido (R3-F2)"
        )
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def approve_booking_via_legacy(self, legacy_agendamento_id: int) -> None:
        """
        Path legado de aprovação — **removido em R3-F2**.

        Antes delegava a ``ReservationService.aprovar``; agora apenas
        registra telemetria/log e falha explicitamente.

        Args:
            legacy_agendamento_id: ID do agendamento legado.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        self._track()
        logger.warning(
            "[acl] approve_booking_via_legacy chamado — path legado removido (R3-F2)"
        )
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def reject_booking_via_legacy(
        self, legacy_agendamento_id: int, reason: str
    ) -> None:
        """
        Path legado de rejeição — **removido em R3-F2**.

        Antes delegava a ``ReservationService.rejeitar``; agora apenas
        registra telemetria/log e falha explicitamente.

        Args:
            legacy_agendamento_id: ID do agendamento legado.
            reason: Motivo da rejeição.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        self._track()
        logger.warning(
            "[acl] reject_booking_via_legacy chamado — path legado removido (R3-F2)"
        )
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def sync_booking_from_agendamento(self, agendamento_id: int) -> Any:
        """
        Sincroniza agendamento legado para core_bookings via LegacySyncService na ACL.

        Args:
            agendamento_id: ID agendamentos.

        Returns:
            Instância CoreBooking ou None.
        """
        self._track()
        from app.modules.catalog.application.legacy_sync_service import LegacySyncService

        logger.debug("[acl] sync_booking_from_agendamento → LegacySyncService")
        return LegacySyncService(self._db).sync_booking_from_agendamento(agendamento_id)

    def resolve_legacy_ids(
        self, catalog_id: int, offering_id: int
    ) -> Tuple[int, int]:
        """
        Resolve IDs legado via LegacySyncService através da ACL.

        Args:
            catalog_id: core_catalog id.
            offering_id: core_offering id.

        Returns:
            Tupla (tranca_id, service_image_id).

        Raises:
            ValueError: Mapeamento inválido.
        """
        self._track()
        from app.modules.catalog.application.legacy_sync_service import LegacySyncService

        return LegacySyncService(self._db).resolve_legacy_ids(catalog_id, offering_id)

    def get_booking_legacy_id(self, booking_id: int, company_id: int) -> Optional[int]:
        """
        Busca legacy_tranca mapping via CoreBooking.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            legacy booking id ou None.
        """
        self._track()
        from app.modules.booking.domain.models import CoreBooking

        row = (
            self._db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.company_id == company_id,
            )
            .first()
        )
        return row.legacy_agendamento_id if row else None

    def project_create_booking(
        self,
        company_id: int,
        customer_id: int,
        tranca_id: int,
        service_image_id: int,
        scheduled_at: Any,
        pricing_total: Any,
        deposit_pct: Any,
        deposit_amount: Any,
        remaining_amount: Any,
        notes: Optional[str] = None,
    ) -> int:
        """
        Projeção outbound: cria ``agendamentos`` + pagamento pendente (ADR-024/025).

        Não faz commit — participa da transação do handler core.

        Args:
            company_id: Tenant.
            customer_id: ID cliente legado.
            tranca_id: ID tranca.
            service_image_id: ID service image.
            scheduled_at: Horário.
            pricing_total: Valor total.
            deposit_pct: Percentual sinal.
            deposit_amount: Valor sinal.
            remaining_amount: Restante.
            notes: Observações.

        Returns:
            ID agendamento legado criado.

        Raises:
            Exception: Qualquer falha deve provocar rollback do handler.
        """
        self._track()
        from decimal import Decimal

        from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
        from app.models.payment import PaymentType
        from app.services.payment_reservation_service import PaymentReservationService

        ag = Agendamento(
            company_id=company_id,
            cliente_id=customer_id,
            tranca_id=tranca_id,
            service_image_id=service_image_id,
            data_hora=scheduled_at,
            valor_total=Decimal(str(pricing_total)),
            percentual_sinal=Decimal(str(deposit_pct)),
            valor_sinal=Decimal(str(deposit_amount)),
            valor_restante=Decimal(str(remaining_amount)),
            observacoes=notes,
            status=ReservationStatus.PENDING_PAYMENT,
            status_pagamento=StatusPagamento.PENDING_PAYMENT,
            sinal_pago=False,
        )
        self._db.add(ag)
        self._db.flush()
        self._db.refresh(ag)
        PaymentReservationService(self._db).criar_pendente(
            ag.id, PaymentType.DEPOSIT, Decimal(str(deposit_amount))
        )
        logger.debug("[acl] project_create_booking agendamento_id=%s", ag.id)
        return ag.id

    def project_approve_booking(self, legacy_agendamento_id: int) -> None:
        """
        Projeção outbound approve — atualiza agendamento sem commit (ADR-024/025).

        Args:
            legacy_agendamento_id: ID agendamentos.

        Raises:
            BusinessRuleError: Sinal não pago (paridade ReservationService).
        """
        self._track()
        from app.core.exceptions import BusinessRuleError
        from app.models.agendamento import Agendamento, ReservationStatus

        ag = (
            self._db.query(Agendamento)
            .filter(Agendamento.id == legacy_agendamento_id)
            .first()
        )
        if not ag:
            raise BusinessRuleError("Agendamento não encontrado")
        if not ag.sinal_pago:
            raise BusinessRuleError("Sinal não pago")
        if ag.status not in (
            ReservationStatus.PENDING_APPROVAL,
            ReservationStatus.WAITING_TIME_CONFIRMATION,
        ):
            raise BusinessRuleError("Reserva não está aguardando aprovação")
        ag.status = ReservationStatus.APPROVED
        ag.horario_aprovado = ag.horario_sugerido or ag.data_hora
        self._db.flush()
        logger.debug("[acl] project_approve_booking agendamento_id=%s", legacy_agendamento_id)

    def project_reject_booking(self, legacy_agendamento_id: int, reason: str) -> None:
        """
        Projeção outbound reject — atualiza agendamento sem commit.

        Args:
            legacy_agendamento_id: ID agendamentos.
            reason: Motivo da rejeição.
        """
        self._track()
        from app.models.agendamento import Agendamento, ReservationStatus

        ag = (
            self._db.query(Agendamento)
            .filter(Agendamento.id == legacy_agendamento_id)
            .first()
        )
        if not ag:
            raise ValueError("Agendamento não encontrado")
        ag.status = ReservationStatus.REJECTED
        ag.motivo_rejeicao = reason
        self._db.flush()
        logger.debug("[acl] project_reject_booking agendamento_id=%s", legacy_agendamento_id)

    def cancel_booking_via_legacy(
        self, legacy_agendamento_id: int, reason: Optional[str] = None
    ) -> None:
        """
        Path legado de cancelamento — **removido em R3-F2**.

        Antes delegava a ``ReservationService.cancelar``; agora apenas
        registra telemetria/log e falha explicitamente.

        Args:
            legacy_agendamento_id: ID agendamentos.
            reason: Motivo opcional.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        self._track()
        logger.warning(
            "[acl] cancel_booking_via_legacy chamado — path legado removido (R3-F2)"
        )
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def project_cancel_booking(
        self, legacy_agendamento_id: int, reason: Optional[str] = None
    ) -> None:
        """
        Projeção outbound cancel — flush only (ADR-024/025).

        Args:
            legacy_agendamento_id: ID agendamentos.
            reason: Motivo opcional.
        """
        self._track()
        from datetime import datetime

        from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
        from app.models.schedule import Schedule, ScheduleStatus

        ag = (
            self._db.query(Agendamento)
            .filter(Agendamento.id == legacy_agendamento_id)
            .first()
        )
        if not ag:
            raise ValueError("Agendamento não encontrado")
        ag.status = ReservationStatus.CANCELLED
        ag.status_pagamento = StatusPagamento.CANCELLED
        ag.deleted_at = datetime.utcnow()
        if reason:
            ag.observacoes = (ag.observacoes or "") + f" | {reason}"
        sch = (
            self._db.query(Schedule)
            .filter(Schedule.agendamento_id == legacy_agendamento_id)
            .first()
        )
        if sch:
            sch.status = ScheduleStatus.CANCELLED
        self._db.flush()
        logger.debug("[acl] project_cancel_booking agendamento_id=%s", legacy_agendamento_id)
