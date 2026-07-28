"""
Command ExpireBooking — CQRS CoreFlow (R4-F13 / ADR-026).

Transição ``pending → expired`` (timeout sem sinal).
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import BusinessRuleError, NotFoundError, VersionConflictError
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
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class ExpireBookingCommand:
    """
    Comando para expirar booking pending.

    Attributes:
        booking_id: ID core_bookings.
        company_id: Tenant.
        reason: Motivo opcional.
        expected_version: Versão If-Match opcional.
        correlation_id: Rastreio HTTP → outbox.
    """

    booking_id: int
    company_id: int
    reason: Optional[str] = None
    expected_version: Optional[int] = None
    correlation_id: Optional[str] = None


class ExpireBookingHandler:
    """
    Handler CQRS — expire core-only (R4-F13).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, command: ExpireBookingCommand) -> CoreBooking:
        """
        Executa expiração de booking pending.

        Args:
            command: Dados validados.

        Returns:
            CoreBooking atualizado.

        Raises:
            NotFoundError: Booking não encontrado.
            VersionConflictError: Optimistic lock.
            BusinessRuleError: Estado inválido ou flag core OFF.
        """
        if not feature_flags.is_enabled("booking.core.enabled"):
            raise BusinessRuleError(
                "Expire exige FEATURE_BOOKING_CORE_ENABLED=true."
            )
        repository = SqlAlchemyCoreBookingRepository(self.db)
        booking = repository.get_by_id(command.booking_id, command.company_id)
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        if (
            command.expected_version is not None
            and booking.version != command.expected_version
        ):
            ArchitectureMetricsStore.get().record_booking_version_conflict()
            raise VersionConflictError()

        expected_version = booking.version
        domain_service = BookingDomainService()
        outbox = OutboxBatch(self.db)
        try:
            try:
                booking = domain_service.expire(
                    booking, command.reason or "expirado"
                )
            except InvalidBookingStateTransitionError as exc:
                raise BusinessRuleError(exc.message) from exc

            booking.legacy = type(booking.legacy)(
                legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                sync_status=SyncStatus.SYNCED,
            )
            booking = repository.save_with_version(booking, expected_version)

            from app.modules.booking.domain.events import booking_expired

            outbox.record(
                booking_expired(
                    company_id=command.company_id,
                    booking_id=booking.id,
                    reason=command.reason or "expirado",
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

        row = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == command.booking_id,
                CoreBooking.company_id == command.company_id,
            )
            .first()
        )
        if not row:
            raise NotFoundError("Booking", str(command.booking_id))
        return row
