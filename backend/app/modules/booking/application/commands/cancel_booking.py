"""
Command CancelBooking — CQRS CoreFlow (R2-F2b).

R2-F0.5: ACL path (flag OFF).
R2-F2b: BookingDomainService.cancel + dual-write + CancelPolicyPort.
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import (
    BusinessRuleError,
    CancelPolicyViolationError,
    NotFoundError,
    ValidationError,
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
from app.modules.booking.infrastructure.adapters.cancel_policy_adapter import (
    LegacyCancelPolicyAdapter,
)
from app.modules.booking.infrastructure.adapters.system_clock_adapter import (
    SystemClockAdapter,
)
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class CancelBookingCommand:
    """
    Comando para cancelar booking genérico.

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


class CancelBookingHandler:
    """
    Handler CQRS — cancel com branch flag OFF (ACL) / ON (domain).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.booking_port = LegacyBookingAdapter(db)

    def execute(self, command: CancelBookingCommand) -> CoreBooking:
        """
        Executa cancelamento de booking.

        Args:
            command: Dados validados.

        Returns:
            CoreBooking atualizado.

        Raises:
            NotFoundError: Booking não encontrado.
            CancelPolicyViolationError: Policy 24h (P07 flag ON).
            VersionConflictError: Optimistic lock.
            BusinessRuleError: Estado inválido.
        """
        if feature_flags.is_enabled("booking.core.enabled"):
            return self._execute_core_path(command)
        return self._execute_legacy_path(command)

    def _execute_legacy_path(self, command: CancelBookingCommand) -> CoreBooking:
        """Path ACL legado (F0.5) — permissivo (P06/P07 flag OFF)."""
        ArchitectureMetricsStore.get().record_booking_cancel_legacy_path()
        booking = self._load_core_row(command)
        if not booking.legacy_agendamento_id:
            raise ValidationError("Booking sem mapeamento legado para cancelamento")

        self.booking_port.cancel_booking_via_legacy(
            booking.legacy_agendamento_id, command.reason
        )

        core = self._sync_core_after_legacy_cancel(booking.legacy_agendamento_id)
        if not core:
            raise ValidationError("Falha ao sincronizar booking após cancelamento")

        from app.modules.booking.domain.events import booking_cancelled
        from app.shared.events.outbox import OutboxService

        OutboxService(self.db).record_and_publish(
            booking_cancelled(
                company_id=command.company_id,
                booking_id=core.id,
                reason=command.reason,
                legacy_agendamento_id=core.legacy_agendamento_id,
                correlation_id=command.correlation_id,
                version=core.version,
            )
        )
        return core

    def _execute_core_path(self, command: CancelBookingCommand) -> CoreBooking:
        """Path domain core (R2-F2b) — dual-write TX ADR-025."""
        ArchitectureMetricsStore.get().record_booking_cancel_core_path()
        repository = SqlAlchemyCoreBookingRepository(self.db)
        cancel_policy = LegacyCancelPolicyAdapter()
        clock = SystemClockAdapter()
        domain_service = BookingDomainService()

        booking = repository.get_by_id(command.booking_id, command.company_id)
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        if command.expected_version is not None and booking.version != command.expected_version:
            ArchitectureMetricsStore.get().record_booking_version_conflict()
            raise VersionConflictError()

        expected_version = booking.version
        if not booking.legacy.legacy_agendamento_id:
            raise ValidationError("Booking sem mapeamento legado para projeção")

        outbox = OutboxBatch(self.db)
        try:
            try:
                booking = domain_service.cancel(
                    booking, cancel_policy, clock, command.reason
                )
            except CancelPolicyViolationError:
                ArchitectureMetricsStore.get().record_booking_cancel_policy_violation()
                raise
            except InvalidBookingStateTransitionError as exc:
                raise BusinessRuleError(exc.message) from exc

            booking.legacy = type(booking.legacy)(
                legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                sync_status=SyncStatus.SYNCED,
            )
            booking = repository.save_with_version(booking, expected_version)

            self.booking_port.project_cancel_booking(
                booking.legacy.legacy_agendamento_id, command.reason
            )

            from app.modules.booking.domain.events import (
                booking_cancelled,
                reservation_cancelled_alias,
            )

            outbox.record(
                booking_cancelled(
                    company_id=command.company_id,
                    booking_id=booking.id,
                    reason=command.reason,
                    legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                    correlation_id=command.correlation_id,
                    version=booking.version,
                )
            )
            outbox.record(
                reservation_cancelled_alias(
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

    def _load_core_row(self, command: CancelBookingCommand) -> CoreBooking:
        """
        Carrega linha ORM core_bookings.

        Args:
            command: Comando com ids.

        Returns:
            CoreBooking ORM.

        Raises:
            NotFoundError: Se ausente.
        """
        booking = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == command.booking_id,
                CoreBooking.company_id == command.company_id,
            )
            .first()
        )
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        return booking

    def _sync_core_after_legacy_cancel(self, legacy_agendamento_id: int) -> CoreBooking:
        """
        Atualiza core_bookings após cancel legado (agendamento com deleted_at).

        Args:
            legacy_agendamento_id: ID agendamentos.

        Returns:
            CoreBooking atualizado ou None.
        """
        from app.models.agendamento import Agendamento

        ag = (
            self.db.query(Agendamento)
            .filter(Agendamento.id == legacy_agendamento_id)
            .first()
        )
        core = (
            self.db.query(CoreBooking)
            .filter(CoreBooking.legacy_agendamento_id == legacy_agendamento_id)
            .first()
        )
        if not ag or not core:
            return core
        core.status = ag.status
        core.payment_status = ag.status_pagamento
        core.deleted_at = ag.deleted_at
        core.version = (core.version or 1) + 1
        self.db.flush()
        self.db.refresh(core)
        return core
