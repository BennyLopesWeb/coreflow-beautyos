"""
Command CreateBooking — CQRS CoreFlow.

R2-F0.5: ACL path (flag OFF).
R2-F1: BookingDomainService core path (flag ON) + dual-write ADR-024/025.
R2-F1b: Idempotency-Key + correlation_id ADR-031.
R3-F2: path core-only — legado (service de reservas via ACL) removido
(ADR-027/ADR-033/RFC-003 M4). Flag ``booking.core.enabled`` OFF agora é
apenas kill-switch de emergência que bloqueia a escrita com
``BusinessRuleError`` (sem fallback).
R4-F2: dual-write outbound (``project_create_booking``) desligado por
padrão — gated por ``booking.legacy.projection.enabled`` (ADR-024 sunset /
RFC-003 M7). Com a flag OFF, o booking é core-only
(``legacy_agendamento_id=None``, ``mark_core_only_synced()``).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    IdempotencyKeyReusedError,
    ValidationError,
)
from app.core.feature_flags import feature_flags
from app.core.telemetry import booking_create_core_span
from app.modules.booking.application.booking_query_service import BookingQueryService
from app.modules.booking.application.booking_response import booking_to_response_dict
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.services.booking_domain_service import BookingDomainService
from app.modules.booking.infrastructure.adapters.catalog_query_adapter import (
    SqlAlchemyCatalogQueryAdapter,
)
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.modules.customer.infrastructure.adapters.customer_query_adapter import (
    SqlAlchemyCustomerQueryAdapter,
)
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.acl.scheduling_port import LegacySchedulingPortAdapter
from app.shared.events.outbox import OutboxBatch
from app.shared.idempotency.idempotency_store import (
    BOOKING_CREATE_ENDPOINT,
    IdempotencyStore,
)


@dataclass(frozen=True)
class CreateBookingCommand:
    """
    Comando para criar reserva via metamodelo genérico.

    Attributes:
        customer_id: ID do cliente (Customer).
        catalog_id: ID core_catalogs.
        offering_id: ID core_offerings.
        scheduled_at: Horário solicitado.
        notes: Observações opcionais.
        company_id: Tenant BeautyOS/CoreFlow.
        idempotency_key: Header Idempotency-Key (F1b).
        request_hash: SHA-256 do body normalizado.
        correlation_id: Rastreio ponta-a-ponta HTTP → outbox.
        resource_id: ID core_resources opcional (R2-F3 / P11).
    """

    customer_id: int
    catalog_id: int
    offering_id: int
    scheduled_at: datetime
    company_id: int
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None
    request_hash: Optional[str] = None
    correlation_id: Optional[str] = None
    resource_id: Optional[int] = None


@dataclass
class CreateBookingResult:
    """
    Resultado do handler incluindo status HTTP idempotente.

    Attributes:
        booking: CoreBooking persistido ou reloaded do cache.
        http_status: 201 primeira execução; 200 retry idempotente.
    """

    booking: CoreBooking
    http_status: int = 201


class CreateBookingHandler:
    """
    Handler CQRS — create booking core-only (R3-F2).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self.booking_port = LegacyBookingAdapter(db)

    def execute(self, command: CreateBookingCommand) -> CreateBookingResult:
        """
        Executa criação de booking com dedupe idempotente (ADR-025).

        Args:
            command: Dados validados do comando.

        Returns:
            CreateBookingResult com booking e status HTTP.

        Raises:
            ValidationError: Mapeamento ou regra inválida.
            ConflictError: Slot indisponível (409).
            IdempotencyKeyReusedError: Mesma key, body diferente.
            BusinessRuleError: Regra de negócio, ou flag ``booking.core.enabled``
                desligada (R3-F2 removeu o path legado — sem fallback).
        """
        cached = self._check_idempotency(command)
        if cached:
            booking = BookingQueryService(self.db).get_booking(
                cached.booking_id, command.company_id
            )
            return CreateBookingResult(booking=booking, http_status=200)

        if not feature_flags.is_enabled("booking.core.enabled"):
            raise BusinessRuleError(
                "Path legado de criação de booking foi removido em R3-F2. "
                "Use /v1/bookings com FEATURE_BOOKING_CORE_ENABLED=true."
            )

        self._outbox_batch = None
        booking = self._execute_core_path(command)

        self._save_idempotency(command, booking)
        outbox = getattr(self, "_outbox_batch", None)
        self.db.commit()
        if outbox:
            outbox.publish_after_commit()
        return CreateBookingResult(booking=booking, http_status=201)

    def _check_idempotency(self, command: CreateBookingCommand) -> Optional[object]:
        """
        Lookup idempotency antes de processar (ADR-025 step 2).

        Args:
            command: Comando com key/hash opcionais.

        Returns:
            IdempotencyCachedResult ou None.

        Raises:
            IdempotencyKeyReusedError: Hash divergente para mesma key.
        """
        if not command.idempotency_key or not command.request_hash:
            return None
        store = IdempotencyStore(self.db)
        try:
            return store.check(
                command.idempotency_key,
                command.company_id,
                BOOKING_CREATE_ENDPOINT,
                command.request_hash,
            )
        except ValueError as exc:
            if str(exc) == "idempotency_key_reused":
                raise IdempotencyKeyReusedError() from exc
            raise

    def _save_idempotency(self, command: CreateBookingCommand, booking: CoreBooking) -> None:
        """
        Persiste snapshot idempotente na TX antes do commit (ADR-025 step 4d).

        Args:
            command: Comando com key/hash.
            booking: Booking criado.

        Returns:
            None
        """
        if not command.idempotency_key or not command.request_hash:
            return
        loaded = BookingQueryService(self.db).get_booking(booking.id, command.company_id)
        response_body = booking_to_response_dict(loaded)
        try:
            IdempotencyStore(self.db).save(
                idempotency_key=command.idempotency_key,
                company_id=command.company_id,
                endpoint=BOOKING_CREATE_ENDPOINT,
                request_hash=command.request_hash,
                response_status=201,
                response_body=response_body,
                booking_id=loaded.id,
            )
        except ValueError as exc:
            if str(exc) == "idempotency_key_reused":
                raise IdempotencyKeyReusedError() from exc
            raise

    def _execute_core_path(self, command: CreateBookingCommand) -> CoreBooking:
        """
        Path domain core (R2-F1) — dual-write TX ADR-025.

        Emite span OTEL ``booking.create.core`` (FF-OBS-001 / R2-F5).

        Args:
            command: Comando.

        Returns:
            CoreBooking SoT.
        """
        with booking_create_core_span(
            company_id=command.company_id,
            catalog_id=command.catalog_id,
            offering_id=command.offering_id,
        ):
            return self._execute_core_path_inner(command)

    def _execute_core_path_inner(self, command: CreateBookingCommand) -> CoreBooking:
        """
        Corpo do path core (extraído para span OTEL).

        Args:
            command: Comando.

        Returns:
            CoreBooking SoT.
        """
        ArchitectureMetricsStore.get().record_booking_create_core_path()

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
        repository = SqlAlchemyCoreBookingRepository(self.db)

        try:
            booking = domain_service.create(
                customer_id=command.customer_id,
                catalog_id=command.catalog_id,
                offering_id=command.offering_id,
                scheduled_at=command.scheduled_at,
                company_id=command.company_id,
                notes=command.notes,
                resource_id=command.resource_id if use_resource_engine else None,
            )
            booking = repository.save(booking)

            legacy_id = None
            if feature_flags.is_enabled("booking.legacy.projection.enabled"):
                tranca_id, service_image_id = self.booking_port.resolve_legacy_ids(
                    command.catalog_id, command.offering_id
                )
                legacy_id = self.booking_port.project_create_booking(
                    company_id=command.company_id,
                    customer_id=command.customer_id,
                    tranca_id=tranca_id,
                    service_image_id=service_image_id,
                    scheduled_at=command.scheduled_at,
                    pricing_total=booking.pricing.price_total,
                    deposit_pct=booking.pricing.deposit_pct,
                    deposit_amount=booking.pricing.deposit_amount,
                    remaining_amount=booking.pricing.remaining_amount,
                    notes=command.notes,
                )
                booking.mark_legacy_synced(legacy_id)
            else:
                booking.mark_core_only_synced()
            booking = repository.save(booking)

            from app.modules.booking.domain.events import booking_created

            outbox = OutboxBatch(self.db)
            outbox.record(
                booking_created(
                    company_id=command.company_id,
                    booking_id=booking.id,
                    customer_id=command.customer_id,
                    catalog_id=command.catalog_id,
                    offering_id=command.offering_id,
                    legacy_agendamento_id=legacy_id,
                    correlation_id=command.correlation_id,
                )
            )

            if use_resource_engine and command.resource_id is not None:
                from app.modules.resource.domain.events import resource_allocated
                from app.modules.resource.infrastructure.adapters.resource_allocation_adapter import (
                    SqlAlchemyResourceAllocationAdapter,
                )

                allocated = SqlAlchemyResourceAllocationAdapter(self.db).allocate(
                    company_id=command.company_id,
                    resource_id=command.resource_id,
                    booking_id=booking.id,
                    starts_at=booking.time_slot.starts_at,
                    ends_at=booking.time_slot.ends_at,
                )
                if allocated:
                    outbox.record(
                        resource_allocated(
                            company_id=command.company_id,
                            resource_id=command.resource_id,
                            booking_id=booking.id,
                            starts_at=booking.time_slot.starts_at.isoformat(),
                            ends_at=booking.time_slot.ends_at.isoformat(),
                            correlation_id=command.correlation_id,
                        )
                    )

            self._outbox_batch = outbox
            if command.correlation_id:
                ArchitectureMetricsStore.get().record_event_correlation_id()

            self.db.flush()
        except Exception:
            ArchitectureMetricsStore.get().record_booking_projection_failure()
            self.db.rollback()
            raise

        core = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking.id,
                CoreBooking.company_id == command.company_id,
            )
            .first()
        )
        if not core:
            raise ValidationError("Falha ao carregar booking após create core")
        return core
