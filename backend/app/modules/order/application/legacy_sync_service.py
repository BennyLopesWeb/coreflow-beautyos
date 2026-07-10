"""
Sincronização Strangler Fig — bookings/agendamentos → ``core_orders``.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
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
    Sincroniza pedidos comerciais a partir de bookings/agendamentos legados.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza todos os agendamentos ativos para core_orders.

        Returns:
            Quantidade processada.
        """
        rows = (
            self.db.query(Agendamento)
            .filter(Agendamento.deleted_at.is_(None))
            .all()
        )
        count = 0
        for ag in rows:
            if self._upsert_from_agendamento(ag):
                count += 1
        self.db.commit()
        logger.info(f"Sync orders: {count}")
        return count

    def sync_one(self, agendamento_id: int) -> Optional[CoreOrder]:
        """
        Sincroniza pedido de um agendamento específico.

        Args:
            agendamento_id: ID ``agendamentos``.

        Returns:
            CoreOrder ou None.
        """
        ag = (
            self.db.query(Agendamento)
            .filter(Agendamento.id == agendamento_id, Agendamento.deleted_at.is_(None))
            .first()
        )
        if not ag:
            return None
        row = self._upsert_from_agendamento(ag)
        self.db.commit()
        return row

    def _upsert_from_agendamento(self, ag: Agendamento) -> Optional[CoreOrder]:
        """
        Cria ou atualiza core_order a partir de Agendamento legado.

        Args:
            ag: Registro legado.

        Returns:
            CoreOrder persistido.
        """
        booking = (
            self.db.query(CoreBooking)
            .filter(CoreBooking.legacy_agendamento_id == ag.id)
            .first()
        )
        status = self._resolve_status(ag)
        paid = self._calc_paid_amount(ag)

        existing = (
            self.db.query(CoreOrder)
            .filter(CoreOrder.legacy_agendamento_id == ag.id)
            .first()
        )
        payload = dict(
            company_id=ag.company_id or 1,
            booking_id=booking.id if booking else None,
            customer_id=ag.cliente_id,
            status=status,
            total_amount=Decimal(str(ag.valor_total)),
            paid_amount=paid,
            currency="BRL",
        )
        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing
        row = CoreOrder(legacy_agendamento_id=ag.id, **payload)
        self.db.add(row)
        return row

    def _resolve_status(self, ag: Agendamento) -> CoreOrderStatus:
        """
        Mapeia status legado para CoreOrderStatus.

        Args:
            ag: Agendamento legado.

        Returns:
            CoreOrderStatus correspondente.
        """
        if ag.status in _CANCELLED:
            return CoreOrderStatus.CANCELLED
        if ag.status_pagamento == StatusPagamento.PAID or ag.status in (
            ReservationStatus.PAID,
            ReservationStatus.COMPLETED,
            ReservationStatus.CONCLUIDO,
        ):
            return CoreOrderStatus.PAID
        return CoreOrderStatus.OPEN

    def _calc_paid_amount(self, ag: Agendamento) -> Decimal:
        """
        Calcula valor pago com base no snapshot da reserva.

        Args:
            ag: Agendamento legado.

        Returns:
            Valor pago acumulado.
        """
        paid = Decimal("0.00")
        if ag.sinal_pago:
            paid += Decimal(str(ag.valor_sinal or 0))
        if ag.status_pagamento == StatusPagamento.PAID:
            return Decimal(str(ag.valor_total))
        if ag.status_pagamento == StatusPagamento.PARTIALLY_PAID:
            return paid
        return paid
