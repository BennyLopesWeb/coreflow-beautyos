"""
Aggregate root Booking — domínio puro (ADR-009).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    LegacyReference,
    MoneySnapshot,
    SyncStatus,
    TimeSlot,
)


@dataclass
class Booking:
    """
    Aggregate root Booking — reserva de offering por customer em um slot.

    R2-F1 implementa factory ``create`` com estado inicial ``pending`` (PENDING_PAYMENT legado).

    Attributes:
        id: Identificador persistido (None antes do save).
        company_id: Tenant (INV-B1).
        customer_id: Cliente.
        catalog_id: Catálogo core.
        offering_id: Offering core.
        time_slot: Intervalo reservado.
        pricing: Snapshot comercial.
        status: Estado canônico.
        notes: Observações opcionais.
        legacy: Referência projeção legado.
        version: Optimistic lock (F2+).
    """

    company_id: int
    customer_id: int
    catalog_id: int
    offering_id: int
    time_slot: TimeSlot
    pricing: MoneySnapshot
    status: BookingLifecycleStatus = BookingLifecycleStatus.PENDING
    notes: Optional[str] = None
    legacy: LegacyReference = field(default_factory=LegacyReference)
    id: Optional[int] = None
    version: int = 1

    @classmethod
    def create(
        cls,
        company_id: int,
        customer_id: int,
        catalog_id: int,
        offering_id: int,
        scheduled_at: datetime,
        ends_at: datetime,
        pricing: MoneySnapshot,
        notes: Optional[str] = None,
    ) -> "Booking":
        """
        Factory para novo booking em estado pending (INV-B1, INV-B2).

        Args:
            company_id: Tenant obrigatório.
            customer_id: ID cliente.
            catalog_id: ID core catalog.
            offering_id: ID core offering.
            scheduled_at: Início do slot.
            ends_at: Fim calculado pela duração do offering.
            pricing: Snapshot de preços.
            notes: Observações.

        Returns:
            Instância Booking pronta para persistência.

        Raises:
            ValueError: Se company_id ausente ou slot inválido.
        """
        if not company_id:
            raise ValueError("company_id is required")
        slot = TimeSlot(starts_at=scheduled_at, ends_at=ends_at)
        return cls(
            company_id=company_id,
            customer_id=customer_id,
            catalog_id=catalog_id,
            offering_id=offering_id,
            time_slot=slot,
            pricing=pricing,
            notes=notes,
            legacy=LegacyReference(sync_status=SyncStatus.PENDING),
        )

    def mark_legacy_synced(self, legacy_agendamento_id: int) -> None:
        """
        Atualiza referência legado após projeção bem-sucedida.

        Args:
            legacy_agendamento_id: ID agendamento criado na projeção.

        Returns:
            None
        """
        self.legacy = LegacyReference(
            legacy_agendamento_id=legacy_agendamento_id,
            sync_status=SyncStatus.SYNCED,
        )

    def approve(self) -> None:
        """
        Transição pending → approved (ADR-026 SM-1).

        Returns:
            None

        Raises:
            InvalidBookingStateTransitionError: Se status != pending.
        """
        from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError

        if self.status != BookingLifecycleStatus.PENDING:
            raise InvalidBookingStateTransitionError()
        self.status = BookingLifecycleStatus.APPROVED

    def reject(self, reason: str) -> None:
        """
        Transição pending → rejected (ADR-026 SM-1).

        Args:
            reason: Motivo da rejeição.

        Returns:
            None

        Raises:
            InvalidBookingStateTransitionError: Se status != pending.
        """
        from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError

        if self.status != BookingLifecycleStatus.PENDING:
            raise InvalidBookingStateTransitionError()
        self.status = BookingLifecycleStatus.REJECTED
        if reason:
            self.notes = reason

    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Transição pending|approved → cancelled (ADR-026 SM-1 / R2-F2b).

        Policy 24h para approved é validada em BookingDomainService via CancelPolicyPort.

        Args:
            reason: Motivo opcional do cancelamento.

        Returns:
            None

        Raises:
            InvalidBookingStateTransitionError: Se status não for pending ou approved.
        """
        from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError

        if self.status not in (
            BookingLifecycleStatus.PENDING,
            BookingLifecycleStatus.APPROVED,
        ):
            raise InvalidBookingStateTransitionError()
        self.status = BookingLifecycleStatus.CANCELLED
        if reason:
            prefix = self.notes or ""
            self.notes = f"{prefix} | {reason}".strip(" |") if prefix else reason
