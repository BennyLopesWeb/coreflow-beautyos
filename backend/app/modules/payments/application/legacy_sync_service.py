"""
Sincronização Strangler Fig — ``payments`` → ``core_payments``.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.agendamento import Agendamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.payments.domain.models import (
    CorePayment,
    CorePaymentStatus,
    CorePaymentType,
)

logger = get_logger("payment_sync")

_TYPE_MAP = {
    PaymentType.DEPOSIT: CorePaymentType.DEPOSIT,
    PaymentType.SINAL: CorePaymentType.DEPOSIT,
    PaymentType.FINAL_PAYMENT: CorePaymentType.FINAL_PAYMENT,
    PaymentType.FINAL: CorePaymentType.FINAL_PAYMENT,
    PaymentType.REFUND: CorePaymentType.REFUND,
    PaymentType.REEMBOLSO: CorePaymentType.REFUND,
}

_STATUS_MAP = {
    PaymentStatus.PENDING: CorePaymentStatus.PENDING,
    PaymentStatus.PENDENTE: CorePaymentStatus.PENDING,
    PaymentStatus.PAID: CorePaymentStatus.PAID,
    PaymentStatus.PAGO: CorePaymentStatus.PAID,
    PaymentStatus.FAILED: CorePaymentStatus.FAILED,
    PaymentStatus.REFUNDED: CorePaymentStatus.REFUNDED,
    PaymentStatus.REEMBOLSADO: CorePaymentStatus.REFUNDED,
}


class PaymentLegacySyncService:
    """
    Sincroniza pagamentos legados para o metamodelo Payment.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza todos os payments ativos.

        Returns:
            Quantidade processada.
        """
        payments = self.db.query(Payment).filter(Payment.deleted_at.is_(None)).all()
        count = 0
        for payment in payments:
            if self._upsert(payment):
                count += 1
        self.db.commit()
        logger.info(f"Sync payments: {count}")
        return count

    def sync_one(self, payment_id: int) -> Optional[CorePayment]:
        """
        Sincroniza um payment legado.

        Args:
            payment_id: ID ``payments``.

        Returns:
            CorePayment ou None.
        """
        payment = (
            self.db.query(Payment)
            .filter(Payment.id == payment_id, Payment.deleted_at.is_(None))
            .first()
        )
        if not payment:
            return None
        row = self._upsert(payment)
        self.db.commit()
        return row

    def _upsert(self, payment: Payment) -> Optional[CorePayment]:
        """
        Cria ou atualiza core_payment.

        Args:
            payment: Registro legado.

        Returns:
            CorePayment ou None se agendamento ausente.
        """
        ag = (
            self.db.query(Agendamento)
            .filter(Agendamento.id == payment.agendamento_id)
            .first()
        )
        if not ag:
            return None

        booking = (
            self.db.query(CoreBooking)
            .filter(CoreBooking.legacy_agendamento_id == ag.id)
            .first()
        )

        existing = (
            self.db.query(CorePayment)
            .filter(CorePayment.legacy_payment_id == payment.id)
            .first()
        )

        ptype = _TYPE_MAP.get(payment.tipo, CorePaymentType.DEPOSIT)
        pstatus = _STATUS_MAP.get(payment.status, CorePaymentStatus.PENDING)

        payload = dict(
            company_id=ag.company_id or 1,
            booking_id=booking.id if booking else None,
            payment_type=ptype,
            amount=Decimal(str(payment.valor)),
            status=pstatus,
            transaction_id=payment.transaction_id,
            receipt_url=payment.comprovante_url,
            paid_at=payment.paid_at,
            legacy_agendamento_id=ag.id,
        )

        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing

        row = CorePayment(legacy_payment_id=payment.id, **payload)
        self.db.add(row)
        return row
