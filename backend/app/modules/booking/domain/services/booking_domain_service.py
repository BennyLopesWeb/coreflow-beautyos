"""
BookingDomainService — regras de criação do aggregate (ADR-009).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Protocol

from app.core.exceptions import BusinessRuleError, ConflictError, ValidationError
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.value_objects.booking_types import MoneySnapshot


@dataclass(frozen=True)
class OfferingSnapshot:
    """
    DTO read-only de offering + catalog para create.

    Args:
        catalog_id: ID core catalog.
        offering_id: ID core offering.
        company_id: Tenant.
        legacy_tranca_id: ID tranca legado.
        legacy_service_image_id: ID service image legado.
        duration_minutes: Duração do serviço.
        pricing: Snapshot monetário.
        catalog_active: Catalog/tranca ativo.
    """

    catalog_id: int
    offering_id: int
    company_id: int
    legacy_tranca_id: int
    legacy_service_image_id: int
    duration_minutes: int
    pricing: MoneySnapshot
    catalog_active: bool = True


class CatalogQueryPort(Protocol):
    """
    Port read-only para dados de catalog/offering (ADR-030 interim F1).
    """

    def get_offering_snapshot(
        self, catalog_id: int, offering_id: int, company_id: int
    ) -> OfferingSnapshot:
        """
        Carrega snapshot comercial e IDs legado.

        Args:
            catalog_id: ID core catalog.
            offering_id: ID core offering.
            company_id: Tenant.

        Returns:
            OfferingSnapshot.

        Raises:
            ValueError: Mapeamento inválido.
        """
        ...


class SchedulingPort(Protocol):
    """Re-export scheduling port contract for domain service typing."""

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
        Verifica disponibilidade completa (slot + conflitos).

        Args:
            company_id: Tenant.
            resource_id: catalog_id interim até Resource Engine F3.
            starts_at: Início.
            ends_at: Fim.
            worker_id: Opcional.
            offering_id: Offering core.
            legacy_tranca_id: ID tranca para paridade legado.
            legacy_service_image_id: ID modelo legado.

        Returns:
            True se disponível.
        """
        ...


class CustomerQueryPort(Protocol):
    """
    Port read-only para validar cliente no create (ADR-025 / R2-F3b).

    ``customer_id`` é o ID legado ``clientes.id`` (FK de core_bookings).
    """

    def get_customer(self, customer_id: int, company_id: int):
        """
        Carrega snapshot do cliente.

        Args:
            customer_id: ID ``clientes``.
            company_id: Tenant.

        Returns:
            Objeto com atributo ``active`` (bool).

        Raises:
            ValueError: Cliente inválido.
        """
        ...


class BookingDomainService:
    """
    Serviço de domínio para operações que envolvem ports externos no create.

    Orquestra invariantes INV-B1–B3 sem conhecer infraestrutura.
    """

    def __init__(
        self,
        catalog_query: Optional[CatalogQueryPort] = None,
        scheduling: Optional[SchedulingPort] = None,
        customer_query: Optional[CustomerQueryPort] = None,
    ):
        """
        Args:
            catalog_query: Port de leitura catalog/offering (obrigatório para create).
            scheduling: Port de disponibilidade (obrigatório para create).
            customer_query: Port de validação de cliente (R2-F3b; opcional legado).
        """
        self._catalog = catalog_query
        self._scheduling = scheduling
        self._customer = customer_query

    def create(
        self,
        customer_id: int,
        catalog_id: int,
        offering_id: int,
        scheduled_at: datetime,
        company_id: int,
        notes: Optional[str] = None,
        resource_id: Optional[int] = None,
    ) -> Booking:
        """
        Cria aggregate Booking após validar offering e slot (INV-B3).

        Args:
            customer_id: ID cliente.
            catalog_id: ID catalog.
            offering_id: ID offering.
            scheduled_at: Horário solicitado.
            company_id: Tenant.
            notes: Observações.
            resource_id: ID core_resources (R2-F3). Se informado com Resource
                Engine ON, valida conflito via ResourcePort (P11).

        Returns:
            Booking aggregate em estado pending.

        Raises:
            ValidationError: Offering inválido, cliente inválido ou no passado.
            BusinessRuleError: Catalog/cliente inativo.
            ConflictError: Slot/resource indisponível (409).
        """
        if scheduled_at.replace(tzinfo=None) < datetime.now():
            raise ValidationError("Não é possível reservar no passado")

        if not self._catalog or not self._scheduling:
            raise ValidationError("Catalog e scheduling ports são obrigatórios para create")

        if self._customer is not None:
            try:
                customer = self._customer.get_customer(customer_id, company_id)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            if not getattr(customer, "active", True):
                raise BusinessRuleError("Cliente inválido ou inativo")

        try:
            snapshot = self._catalog.get_offering_snapshot(
                catalog_id, offering_id, company_id
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        if not snapshot.catalog_active:
            raise BusinessRuleError("Categoria inválida ou inativa")

        duration = max(snapshot.duration_minutes or 30, 30)
        ends_at = scheduled_at + timedelta(minutes=duration)

        # Resource Engine (F3): resource_id = core_resources.id
        # Legacy path: resource_id interim = catalog_id (ACL)
        scheduling_resource_id = resource_id if resource_id is not None else catalog_id
        available = self._scheduling.check_availability(
            company_id=company_id,
            resource_id=scheduling_resource_id,
            starts_at=scheduled_at,
            ends_at=ends_at,
            offering_id=offering_id,
            legacy_tranca_id=snapshot.legacy_tranca_id,
            legacy_service_image_id=snapshot.legacy_service_image_id,
        )
        if not available:
            if resource_id is not None:
                raise ConflictError("resource_unavailable")
            raise ConflictError("slot_unavailable")

        return Booking.create(
            company_id=company_id,
            customer_id=customer_id,
            catalog_id=catalog_id,
            offering_id=offering_id,
            scheduled_at=scheduled_at,
            ends_at=ends_at,
            pricing=snapshot.pricing,
            notes=notes,
        )

    def approve(self, booking: Booking, payment_query: "PaymentQueryPort") -> Booking:
        """
        Aprova booking após validar depósito (ADR-028) e state machine (ADR-026).

        Args:
            booking: Aggregate carregado em pending.
            payment_query: Port read-only de pagamento.

        Returns:
            Aggregate mutado (status approved).

        Raises:
            DepositRequiredError: Sinal não confirmado (P04).
            InvalidBookingStateTransitionError: Estado inválido.
        """
        from app.core.exceptions import DepositRequiredError

        if not payment_query.is_deposit_confirmed(booking.id, booking.company_id):
            raise DepositRequiredError()
        booking.approve()
        return booking

    def reject(self, booking: Booking, reason: str) -> Booking:
        """
        Rejeita booking pending (ADR-026).

        Args:
            booking: Aggregate carregado.
            reason: Motivo.

        Returns:
            Aggregate mutado (status rejected).

        Raises:
            InvalidBookingStateTransitionError: Estado inválido.
        """
        booking.reject(reason)
        return booking

    def cancel(
        self,
        booking: Booking,
        cancel_policy: "CancelPolicyPort",
        clock: "ClockPort",
        reason: Optional[str] = None,
    ) -> Booking:
        """
        Cancela booking pending ou approved (ADR-026 / R2-F2b).

        Args:
            booking: Aggregate carregado.
            cancel_policy: Port de policy (24h para approved).
            clock: Relógio UTC.
            reason: Motivo opcional.

        Returns:
            Aggregate mutado (status cancelled).

        Raises:
            CancelPolicyViolationError: Policy 24h violada (approved).
            InvalidBookingStateTransitionError: Estado terminal ou inválido.
        """
        from app.core.exceptions import CancelPolicyViolationError
        from app.modules.booking.domain.value_objects.booking_types import (
            BookingLifecycleStatus,
        )

        if booking.status == BookingLifecycleStatus.APPROVED:
            if not cancel_policy.may_cancel(booking, clock):
                raise CancelPolicyViolationError()
        elif booking.status != BookingLifecycleStatus.PENDING:
            from app.modules.booking.domain.exceptions import (
                InvalidBookingStateTransitionError,
            )

            raise InvalidBookingStateTransitionError()

        booking.cancel(reason)
        return booking
