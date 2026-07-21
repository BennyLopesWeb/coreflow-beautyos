"""
ACL — Anti-Corruption Layer entre Core e Legado (RFC-002 / R1-F2).

Ports definem contratos core; adapters encapsulam legado.

R3-F2 (ADR-027/ADR-033/RFC-003 M4): os métodos ``*_via_legacy`` **nunca**
delegam mais a ``ReservationService`` — o path de escrita legado foi
removido. Eles apenas registram telemetria ACL, emitem warning e levantam
``BusinessRuleError`` apontando para ``/v1/bookings``.

R4-F2 (ADR-024 sunset / RFC-003 M7): ``project_create_booking`` /
``project_approve_booking`` / ``project_reject_booking`` /
``project_cancel_booking`` (dual-write outbound) tornaram-se **opcionais**
— só chamados pelos commands quando ``booking.legacy.projection.enabled``
estava ON (default ``false``).

R4-F3 (ADR-024 sunset / RFC-003 M7 completo): o dual-write outbound
(``project_*``) foi **removido definitivamente** do código — nenhum
command ainda os invoca e o kill-switch de rollback deixou de existir. O
modelo ``Agendamento`` permanece no banco apenas para dados históricos até
um drop futuro (R4-F4+). ``resolve_legacy_ids`` e ``get_booking_legacy_id``
também foram removidos deste adapter por estarem sem uso — ver
``LegacySyncService.resolve_legacy_ids`` para o path de leitura ainda em
uso pelo ``SchedulingAvailabilityService``. ``sync_booking_from_agendamento``
permanece — continua servindo o path inbound (legado → core).
"""
from typing import Any, Optional, Protocol

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
    legada foi removida. R4-F3: dual-write outbound (``project_*``) também
    removido — apenas ``sync_booking_from_agendamento`` (inbound) permanece.
    """

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

    def cancel_booking_via_legacy(
        self, legacy_agendamento_id: int, reason: Optional[str] = None
    ) -> None:
        """
        Cancela agendamento legado (removido em R3-F2).

        Args:
            legacy_agendamento_id: ID agendamentos.
            reason: Motivo opcional.

        Raises:
            BusinessRuleError: Sempre — path removido em R3-F2.
        """
        ...

    def sync_booking_from_agendamento(self, agendamento_id: int) -> Any:
        """
        Sincroniza agendamento legado (inbound) para core_bookings.

        Args:
            agendamento_id: ID agendamentos.

        Returns:
            Instância CoreBooking ou None.
        """
        ...


class LegacyBookingAdapter:
    """
    Adapter ACL — delega ao legado através de fronteira explícita.

    R1-F2: wiring implementado; commands CQRS migram para adapter em Release 2.
    R3-F2: métodos ``*_via_legacy`` (create/approve/reject/cancel) não
    delegam mais a ``ReservationService`` — sempre levantam
    ``BusinessRuleError`` apontando para ``/v1/bookings`` (ADR-027/ADR-033).
    R4-F3: dual-write outbound (``project_*``) removido definitivamente —
    apenas ``sync_booking_from_agendamento`` (inbound legado → core)
    permanece funcional.
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
