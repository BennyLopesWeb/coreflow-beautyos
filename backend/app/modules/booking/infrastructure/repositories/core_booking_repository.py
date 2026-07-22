"""
SQLAlchemy adapter para CoreBookingRepository (ADR-030 / R2-F2 optimistic lock).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import OptimisticLockConflictError
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    LegacyReference,
    MoneySnapshot,
    SyncStatus,
    TimeSlot,
)

_LIFECYCLE_TO_ORM = {
    BookingLifecycleStatus.PENDING: ReservationStatus.PENDING_PAYMENT,
    BookingLifecycleStatus.APPROVED: ReservationStatus.APPROVED,
    BookingLifecycleStatus.REJECTED: ReservationStatus.REJECTED,
    BookingLifecycleStatus.CANCELLED: ReservationStatus.CANCELLED,
    BookingLifecycleStatus.RESCHEDULED: ReservationStatus.RESCHEDULED,
}

_ORM_TO_LIFECYCLE = {
    ReservationStatus.PENDING_PAYMENT: BookingLifecycleStatus.PENDING,
    ReservationStatus.PENDING_APPROVAL: BookingLifecycleStatus.PENDING,
    ReservationStatus.WAITING_TIME_CONFIRMATION: BookingLifecycleStatus.PENDING,
    ReservationStatus.APPROVED: BookingLifecycleStatus.APPROVED,
    ReservationStatus.REJECTED: BookingLifecycleStatus.REJECTED,
    ReservationStatus.CANCELLED: BookingLifecycleStatus.CANCELLED,
    ReservationStatus.RESCHEDULED: BookingLifecycleStatus.RESCHEDULED,
    ReservationStatus.PENDENTE: BookingLifecycleStatus.PENDING,
    ReservationStatus.CONFIRMADO: BookingLifecycleStatus.APPROVED,
}


class SqlAlchemyCoreBookingRepository:
    """
    Persiste aggregate Booking em ``core_bookings``.

    Args:
        db: Sessão SQLAlchemy (Unit of Work por request).
    """

    def __init__(self, db: Session):
        self._db = db

    def _lifecycle_from_orm(self, status) -> BookingLifecycleStatus:
        """
        Mapeia ReservationStatus ORM → lifecycle domain.

        Args:
            status: Valor enum ou string do ORM.

        Returns:
            BookingLifecycleStatus.
        """
        if hasattr(status, "value"):
            key = ReservationStatus(status.value) if isinstance(status.value, str) else status
        else:
            key = ReservationStatus(status)
        return _ORM_TO_LIFECYCLE.get(key, BookingLifecycleStatus.PENDING)

    def _resolve_duration_minutes(self, row: CoreBooking) -> int:
        """
        Resolve duração do offering para reconstruir TimeSlot no load (TD-R2-F2-002).

        Args:
            row: Linha core_bookings com offering_id.

        Returns:
            Duração em minutos (≥30 fallback apenas se offering sem duração).
        """
        from app.modules.catalog.domain.models import CoreOffering

        offering = (
            self._db.query(CoreOffering)
            .filter(
                CoreOffering.id == row.offering_id,
                CoreOffering.company_id == row.company_id,
                CoreOffering.deleted_at.is_(None),
            )
            .first()
        )
        if offering and offering.duration_minutes:
            return max(int(offering.duration_minutes), 1)
        return 30

    def _to_domain(self, row: CoreBooking) -> Booking:
        """
        Mapeia ORM → aggregate.

        Args:
            row: Linha core_bookings.

        Returns:
            Booking domain entity.
        """
        sync = SyncStatus(row.sync_status) if row.sync_status else SyncStatus.SYNCED
        duration = self._resolve_duration_minutes(row)
        ends_at = row.scheduled_at + timedelta(minutes=duration)
        return Booking(
            id=row.id,
            company_id=row.company_id,
            customer_id=row.customer_id,
            catalog_id=row.catalog_id,
            offering_id=row.offering_id,
            time_slot=TimeSlot(starts_at=row.scheduled_at, ends_at=ends_at),
            pricing=MoneySnapshot(
                price_total=Decimal(str(row.price_total)),
                deposit_pct=Decimal(str(row.deposit_pct)),
                deposit_amount=Decimal(str(row.deposit_amount)),
                remaining_amount=Decimal(str(row.remaining_amount)),
            ),
            status=self._lifecycle_from_orm(row.status),
            notes=row.notes,
            legacy=LegacyReference(
                legacy_agendamento_id=row.legacy_agendamento_id,
                sync_status=sync,
            ),
            version=row.version or 1,
        )

    def _apply_domain(self, row: CoreBooking, booking: Booking) -> None:
        """
        Aplica campos do aggregate na linha ORM.

        Args:
            row: Linha ORM mutável.
            booking: Aggregate fonte.

        Returns:
            None
        """
        row.company_id = booking.company_id
        row.customer_id = booking.customer_id
        row.catalog_id = booking.catalog_id
        row.offering_id = booking.offering_id
        row.scheduled_at = booking.time_slot.starts_at
        row.status = _LIFECYCLE_TO_ORM.get(
            booking.status, ReservationStatus.PENDING_PAYMENT
        )
        if booking.status == BookingLifecycleStatus.APPROVED:
            row.approved_at = row.approved_at or datetime.utcnow()
            row.payment_status = StatusPagamento.PARTIALLY_PAID
        if booking.status == BookingLifecycleStatus.CANCELLED:
            row.payment_status = StatusPagamento.CANCELLED
            row.deleted_at = row.deleted_at or datetime.utcnow()
        row.price_total = booking.pricing.price_total
        row.deposit_pct = booking.pricing.deposit_pct
        row.deposit_amount = booking.pricing.deposit_amount
        row.remaining_amount = booking.pricing.remaining_amount
        row.notes = booking.notes
        row.legacy_agendamento_id = booking.legacy.legacy_agendamento_id
        row.sync_status = booking.legacy.sync_status.value

    def save(self, booking: Booking) -> Booking:
        """
        Insert ou update core_bookings (create path — sem optimistic gate).

        Args:
            booking: Aggregate.

        Returns:
            Booking com id e version atualizada.
        """
        if booking.id:
            row = (
                self._db.query(CoreBooking)
                .filter(
                    CoreBooking.id == booking.id,
                    CoreBooking.company_id == booking.company_id,
                )
                .first()
            )
            if not row:
                raise ValueError(f"Booking {booking.id} not found")
            expected = row.version or 1
            self._apply_domain(row, booking)
            row.version = expected + 1
            booking.version = row.version
        else:
            row = CoreBooking()
            self._db.add(row)
            self._apply_domain(row, booking)
            row.version = 1
            booking.version = 1

        self._db.flush()
        self._db.refresh(row)
        booking.id = row.id
        return booking

    def save_with_version(self, booking: Booking, expected_version: int) -> Booking:
        """
        Update com optimistic lock (ADR-031).

        Args:
            booking: Aggregate após transição de estado.
            expected_version: Versão lida antes da mutação.

        Returns:
            Booking com version incrementada.

        Raises:
            OptimisticLockConflictError: Se version divergiu.
        """
        if not booking.id:
            raise ValueError("save_with_version requires persisted booking")

        row = (
            self._db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking.id,
                CoreBooking.company_id == booking.company_id,
                CoreBooking.version == expected_version,
                CoreBooking.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise OptimisticLockConflictError()

        self._apply_domain(row, booking)
        row.version = expected_version + 1
        row.sync_status = booking.legacy.sync_status.value
        self._db.flush()
        self._db.refresh(row)
        booking.version = row.version
        return booking

    def get_by_id(self, booking_id: int, company_id: int) -> Optional[Booking]:
        """
        Carrega booking por id.

        Args:
            booking_id: ID.
            company_id: Tenant.

        Returns:
            Booking ou None.
        """
        row = (
            self._db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.company_id == company_id,
                CoreBooking.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            return None
        return self._to_domain(row)
