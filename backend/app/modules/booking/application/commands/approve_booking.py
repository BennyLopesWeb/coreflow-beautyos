"""
Command ApproveBooking — CQRS CoreFlow.

R2-F0.5: ACL path (flag OFF).
R2-F2: BookingDomainService.approve + dual-write + optimistic lock.
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import (
    BusinessRuleError,
    DepositRequiredError,
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
from app.modules.booking.infrastructure.adapters.payment_query_adapter import (
    LegacyPaymentQueryAdapter,
)
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class ApproveBookingCommand:
    """
    Comando para aprovar booking genérico (admin).

    Attributes:
        booking_id: ID core_bookings.
        company_id: Tenant.
        expected_version: Versão If-Match opcional.
        correlation_id: Rastreio HTTP → outbox.
    """

    booking_id: int
    company_id: int
    expected_version: Optional[int] = None
    correlation_id: Optional[str] = None


class ApproveBookingHandler:
    """
    Handler CQRS — approve com branch flag OFF (ACL) / ON (domain).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.booking_port = LegacyBookingAdapter(db)

    def execute(self, command: ApproveBookingCommand) -> CoreBooking:
        """
        Executa aprovação de booking.

        Args:
            command: Dados validados.

        Returns:
            CoreBooking atualizado.

        Raises:
            NotFoundError: Booking não encontrado.
            DepositRequiredError: P04 — sinal não pago.
            VersionConflictError: Optimistic lock.
            BusinessRuleError: Regra de negócio / estado inválido.
        """
        if feature_flags.is_enabled("booking.core.enabled"):
            return self._execute_core_path(command)
        return self._execute_legacy_path(command)

    def _execute_legacy_path(self, command: ApproveBookingCommand) -> CoreBooking:
        """Path ACL legado (F0.5) — inalterado exceto métricas F2."""
        ArchitectureMetricsStore.get().record_booking_approve_legacy_path()
        booking = self._load_core_row(command)
        if not booking.legacy_agendamento_id:
            raise ValidationError("Booking sem mapeamento legado para aprovação")

        try:
            self.booking_port.approve_booking_via_legacy(booking.legacy_agendamento_id)
        except BusinessRuleError as exc:
            if "Sinal" in str(exc.detail) or "sinal" in str(exc.detail).lower():
                ArchitectureMetricsStore.get().record_booking_deposit_required()
                raise DepositRequiredError() from exc
            raise

        core = self.booking_port.sync_booking_from_agendamento(
            booking.legacy_agendamento_id
        )
        if not core:
            raise ValidationError("Falha ao sincronizar booking após aprovação")

        from app.modules.booking.domain.events import booking_approved
        from app.shared.events.outbox import OutboxService

        OutboxService(self.db).record_and_publish(
            booking_approved(
                company_id=command.company_id,
                booking_id=core.id,
                legacy_agendamento_id=core.legacy_agendamento_id,
                correlation_id=command.correlation_id,
                version=core.version,
            )
        )
        return core

    def _execute_core_path(self, command: ApproveBookingCommand) -> CoreBooking:
        """Path domain core (R2-F2) — dual-write TX ADR-025."""
        ArchitectureMetricsStore.get().record_booking_approve_core_path()
        repository = SqlAlchemyCoreBookingRepository(self.db)
        payment_query = LegacyPaymentQueryAdapter(self.db)
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
                booking = domain_service.approve(booking, payment_query)
            except DepositRequiredError:
                ArchitectureMetricsStore.get().record_booking_deposit_required()
                raise
            except InvalidBookingStateTransitionError as exc:
                raise BusinessRuleError(exc.message) from exc

            booking.legacy = type(booking.legacy)(
                legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                sync_status=SyncStatus.SYNCED,
            )
            booking = repository.save_with_version(booking, expected_version)

            self.booking_port.project_approve_booking(
                booking.legacy.legacy_agendamento_id
            )

            from app.modules.booking.domain.events import (
                booking_approved,
                reservation_approved_alias,
            )

            outbox.record(
                booking_approved(
                    company_id=command.company_id,
                    booking_id=booking.id,
                    legacy_agendamento_id=booking.legacy.legacy_agendamento_id,
                    correlation_id=command.correlation_id,
                    version=booking.version,
                )
            )
            outbox.record(
                reservation_approved_alias(
                    company_id=command.company_id,
                    booking_id=booking.id,
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

        core = self._load_core_row(command)
        return core

    def _load_core_row(self, command: ApproveBookingCommand) -> CoreBooking:
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
                CoreBooking.deleted_at.is_(None),
            )
            .first()
        )
        if not booking:
            raise NotFoundError("Booking", str(command.booking_id))
        return booking
