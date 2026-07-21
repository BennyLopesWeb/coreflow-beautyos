"""
Command RejectBooking — CQRS CoreFlow.

R2-F0.5: ACL path (flag OFF).
R2-F2: BookingDomainService.reject + dual-write + optimistic lock.
R3-F2: path core-only — legado (service de reservas via ACL) removido
(ADR-027/ADR-033/RFC-003 M4). Flag ``booking.core.enabled`` OFF é
kill-switch de emergência que bloqueia a escrita com ``BusinessRuleError``
(sem fallback legado).
R4-F2: ``legacy_agendamento_id`` deixou de ser obrigatório. ``project_*``
só é chamado com ``booking.legacy.projection.enabled`` ON **e** id legado
presente (ADR-024 sunset / RFC-003 M7).
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    VersionConflictError,
)
from app.core.feature_flags import feature_flags
from app.modules.booking.domain.exceptions import (
    InvalidBookingStateTransitionError,
    OptimisticLockConflictError,
)
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.services.booking_domain_service import BookingDomainService
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class RejectBookingCommand:
    """
    Comando para rejeitar booking genérico (admin).

    Attributes:
        booking_id: ID core_bookings.
        company_id: Tenant.
        reason: Motivo da rejeição.
        expected_version: Versão If-Match opcional.
        correlation_id: Rastreio HTTP → outbox.
    """

    booking_id: int
    company_id: int
    reason: str
    expected_version: Optional[int] = None
    correlation_id: Optional[str] = None


class RejectBookingHandler:
    """
    Handler CQRS — reject core-only (R3-F2).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.booking_port = LegacyBookingAdapter(db)

    def execute(self, command: RejectBookingCommand) -> CoreBooking:
        """
        Executa rejeição de booking.

        Args:
            command: Dados validados.

        Returns:
            CoreBooking atualizado.

        Raises:
            BusinessRuleError: Flag ``booking.core.enabled`` desligada
                (R3-F2 removeu o path legado — sem fallback).
        """
        if not feature_flags.is_enabled("booking.core.enabled"):
            raise BusinessRuleError(
                "Path legado de rejeição de booking foi removido em R3-F2. "
                "Use /v1/bookings com FEATURE_BOOKING_CORE_ENABLED=true."
            )
        return self._execute_core_path(command)

    def _execute_core_path(self, command: RejectBookingCommand) -> CoreBooking:
        """Path domain core (R2-F2)."""
        ArchitectureMetricsStore.get().record_booking_reject_core_path()
        repository = SqlAlchemyCoreBookingRepository(self.db)
        domain_service = BookingDomainService()

        booking = repository.get_by_id(command.booking_id, command.company_id)
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        if command.expected_version is not None and booking.version != command.expected_version:
            ArchitectureMetricsStore.get().record_booking_version_conflict()
            raise VersionConflictError()

        expected_version = booking.version

        outbox = OutboxBatch(self.db)
        try:
            try:
                booking = domain_service.reject(booking, command.reason)
            except InvalidBookingStateTransitionError as exc:
                raise BusinessRuleError(exc.message) from exc

            booking.legacy = type(booking.legacy)(
                legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                sync_status=SyncStatus.SYNCED,
            )
            booking = repository.save_with_version(booking, expected_version)

            if booking.legacy.legacy_agendamento_id and feature_flags.is_enabled(
                "booking.legacy.projection.enabled"
            ):
                self.booking_port.project_reject_booking(
                    booking.legacy.legacy_agendamento_id, command.reason
                )

            from app.modules.booking.domain.events import booking_rejected

            outbox.record(
                booking_rejected(
                    company_id=command.company_id,
                    booking_id=booking.id,
                    reason=command.reason,
                    legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                    correlation_id=command.correlation_id,
                    version=booking.version,
                )
            )
            if command.correlation_id:
                ArchitectureMetricsStore.get().record_event_correlation_id()

            self.db.commit()
            outbox.publish_after_commit()
        except OptimisticLockConflictError as exc:
            ArchitectureMetricsStore.get().record_booking_version_conflict()
            self.db.rollback()
            raise VersionConflictError() from exc
        except Exception:
            self.db.rollback()
            raise

        return self._load_core_row(command)

    def _load_core_row(self, command: RejectBookingCommand) -> CoreBooking:
        """Carrega CoreBooking ORM."""
        booking = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == command.booking_id,
                CoreBooking.company_id == command.company_id,
                CoreBooking.deleted_at.is_(None),
            )
            .first()
        )
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        return booking
