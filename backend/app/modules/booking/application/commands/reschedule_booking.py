"""
Command RescheduleBooking — CQRS CoreFlow (R4-F11 / R4-F12 / ADR-026).

Fecha o booking approved como ``rescheduled`` e cria um novo booking no
horário solicitado (mesmo customer/catalog/offering). Transfere
``deposit_paid`` / ``payment_status`` do booking antigo; se o sinal já
estava pago, o novo booking nasce ``approved``.

R4-F12: além dos flags ORM, reatribui linhas ``payments`` e
``core_payments`` (``booking_id``) do booking antigo para o novo —
paridade contábil/auditoria para ``GET /v1/payments?booking_id=``.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import BusinessRuleError, NotFoundError, VersionConflictError
from app.core.feature_flags import feature_flags
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.modules.booking.domain.exceptions import (
    InvalidBookingStateTransitionError,
    OptimisticLockConflictError,
)
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.services.booking_domain_service import BookingDomainService
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.booking.infrastructure.adapters.catalog_query_adapter import (
    SqlAlchemyCatalogQueryAdapter,
)
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.modules.customer.infrastructure.adapters.customer_query_adapter import (
    SqlAlchemyCustomerQueryAdapter,
)
from app.shared.acl.scheduling_port import LegacySchedulingPortAdapter
from app.shared.events.outbox import OutboxBatch


@dataclass(frozen=True)
class RescheduleBookingCommand:
    """
    Comando para reagendar booking genérico (R4-F11).

    Attributes:
        booking_id: ID do booking a fechar (``rescheduled``).
        company_id: Tenant.
        scheduled_at: Novo horário do booking substituto.
        notes: Motivo/mensagem opcional.
        expected_version: Versão If-Match opcional do booking antigo.
        correlation_id: Rastreio HTTP → outbox.
        resource_id: ID core_resources opcional (Resource Engine).
    """

    booking_id: int
    company_id: int
    scheduled_at: datetime
    notes: Optional[str] = None
    expected_version: Optional[int] = None
    correlation_id: Optional[str] = None
    resource_id: Optional[int] = None


@dataclass(frozen=True)
class RescheduleBookingResult:
    """
    Resultado do reagendamento.

    Attributes:
        previous: Booking antigo com status ``rescheduled``.
        booking: Booking novo criado no horário solicitado.
    """

    previous: CoreBooking
    booking: CoreBooking


class RescheduleBookingHandler:
    """
    Handler CQRS — reagendamento core-only (R4-F11 / ADR-026).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, command: RescheduleBookingCommand) -> RescheduleBookingResult:
        """
        Fecha booking approved e cria substituto no novo horário.

        Args:
            command: Dados validados.

        Returns:
            RescheduleBookingResult com previous + booking novo.

        Raises:
            NotFoundError: Booking antigo não encontrado.
            VersionConflictError: Optimistic lock.
            BusinessRuleError: Estado inválido ou flag core OFF.
            ConflictError: Slot indisponível (via domain create).
            ValidationError: Horário no passado / offering inválido.
        """
        if not feature_flags.is_enabled("booking.core.enabled"):
            raise BusinessRuleError(
                "Path de reagendamento exige FEATURE_BOOKING_CORE_ENABLED=true."
            )
        return self._execute_core_path(command)

    def _execute_core_path(
        self, command: RescheduleBookingCommand
    ) -> RescheduleBookingResult:
        """
        Path domain: reschedule antigo + create novo na mesma TX.

        Args:
            command: Comando.

        Returns:
            RescheduleBookingResult.
        """
        repository = SqlAlchemyCoreBookingRepository(self.db)
        old = repository.get_by_id(command.booking_id, command.company_id)
        if not old:
            raise NotFoundError("Booking", str(command.booking_id))
        if (
            command.expected_version is not None
            and old.version != command.expected_version
        ):
            ArchitectureMetricsStore.get().record_booking_version_conflict()
            raise VersionConflictError()

        expected_version = old.version
        deposit_paid = self._load_deposit_paid(command.booking_id, command.company_id)
        payment_status = self._load_payment_status(
            command.booking_id, command.company_id
        )

        use_resource_engine = feature_flags.is_enabled("resource.engine.enabled")
        if use_resource_engine and command.resource_id is not None:
            from app.modules.resource.infrastructure.adapters.scheduling_resource_port_adapter import (
                SchedulingResourcePortAdapter,
            )

            scheduling_port = SchedulingResourcePortAdapter(self.db)
        else:
            scheduling_port = LegacySchedulingPortAdapter(self.db)

        domain_service = BookingDomainService(
            catalog_query=SqlAlchemyCatalogQueryAdapter(self.db),
            scheduling=scheduling_port,
            customer_query=SqlAlchemyCustomerQueryAdapter(self.db),
        )

        outbox = OutboxBatch(self.db)
        try:
            try:
                old = domain_service.reschedule(old, command.notes)
            except InvalidBookingStateTransitionError as exc:
                raise BusinessRuleError(exc.message) from exc

            old.legacy = type(old.legacy)(
                legacy_agendamento_id=old.legacy.legacy_agendamento_id,
                sync_status=SyncStatus.SYNCED,
            )
            old = repository.save_with_version(old, expected_version)
            self.db.flush()

            reason_note = command.notes or f"Reagendado de booking #{command.booking_id}"
            new_booking = domain_service.create(
                customer_id=old.customer_id,
                catalog_id=old.catalog_id,
                offering_id=old.offering_id,
                scheduled_at=command.scheduled_at,
                company_id=command.company_id,
                notes=reason_note,
                resource_id=command.resource_id if use_resource_engine else None,
            )
            new_booking.mark_core_only_synced()
            new_booking = repository.save(new_booking)
            self.db.flush()

            new_row = self._apply_payment_parity(
                new_booking.id,
                command.company_id,
                deposit_paid=deposit_paid,
                payment_status=payment_status,
            )
            self._transfer_payment_rows(
                from_booking_id=command.booking_id,
                to_booking_id=new_row.id,
            )

            from app.modules.booking.domain.events import (
                booking_created,
                booking_rescheduled,
            )

            outbox.record(
                booking_rescheduled(
                    company_id=command.company_id,
                    booking_id=command.booking_id,
                    new_booking_id=new_row.id,
                    scheduled_at=command.scheduled_at.isoformat(),
                    reason=command.notes,
                    correlation_id=command.correlation_id,
                    version=old.version,
                )
            )
            outbox.record(
                booking_created(
                    company_id=command.company_id,
                    booking_id=new_row.id,
                    customer_id=new_row.customer_id,
                    catalog_id=new_row.catalog_id,
                    offering_id=new_row.offering_id,
                    legacy_agendamento_id=None,
                    correlation_id=command.correlation_id,
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

        previous = self._load_core_row(command.booking_id, command.company_id)
        created = self._load_core_row(new_row.id, command.company_id)
        return RescheduleBookingResult(previous=previous, booking=created)

    def _load_deposit_paid(self, booking_id: int, company_id: int) -> bool:
        """
        Lê ``deposit_paid`` do ORM antes de fechar o booking.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            Valor de ``deposit_paid``.
        """
        row = self._load_core_row(booking_id, company_id)
        return bool(row.deposit_paid)

    def _load_payment_status(self, booking_id: int, company_id: int) -> StatusPagamento:
        """
        Lê ``payment_status`` do ORM antes de fechar o booking.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            StatusPagamento atual.
        """
        row = self._load_core_row(booking_id, company_id)
        status = row.payment_status
        if hasattr(status, "value"):
            return StatusPagamento(status.value)
        return StatusPagamento(status)

    def _apply_payment_parity(
        self,
        booking_id: int,
        company_id: int,
        *,
        deposit_paid: bool,
        payment_status: StatusPagamento,
    ) -> CoreBooking:
        """
        Transfere sinal/pagamento do booking antigo para o novo.

        Se o sinal já estava pago, o novo booking fica ``approved``
        (paridade operacional com o booking substituído).

        Args:
            booking_id: ID do booking novo.
            company_id: Tenant.
            deposit_paid: Se o antigo tinha sinal confirmado.
            payment_status: Status de pagamento do antigo.

        Returns:
            CoreBooking ORM atualizado.
        """
        row = self._load_core_row(booking_id, company_id)
        row.deposit_paid = deposit_paid
        row.payment_status = payment_status
        if deposit_paid:
            row.status = ReservationStatus.APPROVED
            row.approved_at = datetime.utcnow()
        self.db.flush()
        return row

    def _transfer_payment_rows(
        self, *, from_booking_id: int, to_booking_id: int
    ) -> int:
        """
        Reatribui ``payments`` e ``core_payments`` do booking antigo ao novo (R4-F12).

        Garante que o sinal confirmado no booking substituído continue
        visível em ``GET /v1/payments?booking_id={novo}`` e na ponte
        ``Payment.booking_id`` — sem duplicar linhas nem criar Financeiro
        de novo (o movimento contábil histórico permanece).

        Args:
            from_booking_id: ID do booking ``rescheduled``.
            to_booking_id: ID do booking substituto.

        Returns:
            Quantidade de linhas ``payments`` reatribuídas.
        """
        from app.models.payment import Payment
        from app.modules.payments.domain.models import CorePayment

        moved = (
            self.db.query(Payment)
            .filter(
                Payment.booking_id == from_booking_id,
                Payment.deleted_at.is_(None),
            )
            .update({Payment.booking_id: to_booking_id}, synchronize_session=False)
        )
        self.db.query(CorePayment).filter(
            CorePayment.booking_id == from_booking_id,
        ).update(
            {CorePayment.booking_id: to_booking_id},
            synchronize_session=False,
        )
        self.db.flush()
        return int(moved or 0)

    def _load_core_row(self, booking_id: int, company_id: int) -> CoreBooking:
        """
        Carrega linha ORM core_bookings.

        Args:
            booking_id: ID.
            company_id: Tenant.

        Returns:
            CoreBooking.

        Raises:
            NotFoundError: Se ausente.
        """
        booking = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.company_id == company_id,
            )
            .first()
        )
        if not booking:
            raise NotFoundError("Booking", str(booking_id))
        return booking
