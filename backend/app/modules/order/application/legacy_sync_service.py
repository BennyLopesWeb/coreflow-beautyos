"""
Sincronização Strangler Fig — bookings → ``core_orders``.

.. deprecated:: 2.11.0-r4-f8
    Sincronizava a partir de ``Agendamento`` legado (``sync_all`` varria
    ``agendamentos``, ``sync_one`` recebia ``agendamento_id``). A tabela
    foi removida (DROP físico — ADR-024 sunset / RFC-003 M11+) —
    ``sync_all`` tornou-se no-op (nenhum caminho de escrita ativo cria
    ``Agendamento`` desde R3-F2/R4-F3/R4-F4, então não há mais nada a
    sincronizar por essa direção) e ``sync_one`` passou a receber
    ``booking_id`` (``core_bookings.id``) diretamente — equivalente
    core-only, sem depender da tabela removida.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.modules.booking.domain.models import CoreBooking
from app.modules.order.domain.models import CoreOrder, CoreOrderStatus

logger = get_logger("order_sync")

_CANCELLED = {
    ReservationStatus.REJECTED,
    ReservationStatus.CANCELLED,
    ReservationStatus.CANCELADO,
    ReservationStatus.NO_SHOW,
}


class OrderLegacySyncService:
    """
    Sincroniza pedidos comerciais a partir de bookings (``CoreBooking``).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza pedidos legado ativos para core_orders.

        .. deprecated:: 2.11.0-r4-f8
            A tabela ``agendamentos`` foi removida — no-op (``0``). Use
            ``sync_one(booking_id)`` para sincronizar um ``CoreBooking``
            específico sob demanda.

        Returns:
            ``0`` — sempre no-op.
        """
        return 0

    def sync_one(self, booking_id: int) -> Optional[CoreOrder]:
        """
        Sincroniza pedido de um booking core específico.

        .. deprecated:: 2.11.0-r4-f8
            Assinatura alterada de ``agendamento_id`` para ``booking_id``
            (``core_bookings.id``) — a tabela ``agendamentos`` foi
            removida (DROP físico R4-F8).

        Args:
            booking_id: ID ``core_bookings.id``.

        Returns:
            CoreOrder ou None se o booking não existir.
        """
        booking = (
            self.db.query(CoreBooking)
            .filter(CoreBooking.id == booking_id, CoreBooking.deleted_at.is_(None))
            .first()
        )
        if not booking:
            return None
        row = self._upsert_from_booking(booking)
        self.db.commit()
        return row

    def _upsert_from_booking(self, booking: CoreBooking) -> Optional[CoreOrder]:
        """
        Cria ou atualiza core_order a partir de um ``CoreBooking``.

        Args:
            booking: Booking core.

        Returns:
            CoreOrder persistido.
        """
        status = self._resolve_status(booking)
        paid = self._calc_paid_amount(booking)

        existing = (
            self.db.query(CoreOrder)
            .filter(CoreOrder.booking_id == booking.id)
            .first()
        )
        payload = dict(
            company_id=booking.company_id,
            booking_id=booking.id,
            customer_id=booking.customer_id,
            status=status,
            total_amount=Decimal(str(booking.price_total)),
            paid_amount=paid,
            currency="BRL",
        )
        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing
        row = CoreOrder(legacy_agendamento_id=booking.legacy_agendamento_id, **payload)
        self.db.add(row)
        return row

    def _resolve_status(self, booking: CoreBooking) -> CoreOrderStatus:
        """
        Mapeia status do booking para CoreOrderStatus.

        Args:
            booking: Booking core.

        Returns:
            CoreOrderStatus correspondente.
        """
        if booking.status in _CANCELLED:
            return CoreOrderStatus.CANCELLED
        if booking.payment_status == StatusPagamento.PAID or booking.status in (
            ReservationStatus.PAID,
            ReservationStatus.COMPLETED,
            ReservationStatus.CONCLUIDO,
        ):
            return CoreOrderStatus.PAID
        return CoreOrderStatus.OPEN

    def _calc_paid_amount(self, booking: CoreBooking) -> Decimal:
        """
        Calcula valor pago com base no snapshot do booking.

        Args:
            booking: Booking core.

        Returns:
            Valor pago acumulado.
        """
        paid = Decimal("0.00")
        if booking.deposit_paid:
            paid += Decimal(str(booking.deposit_amount or 0))
        if booking.payment_status == StatusPagamento.PAID:
            return Decimal(str(booking.price_total))
        if booking.payment_status == StatusPagamento.PARTIALLY_PAID:
            return paid
        return paid
