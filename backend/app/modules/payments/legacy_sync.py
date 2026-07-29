"""
Sincronização Strangler Fig — ``payments`` → ``core_payments``.

``Payment`` é a fonte primária de escrita; ``CorePayment`` é espelho
derivado. O sync explícito (``sync_payment``) deve ser chamado após
writes legítimos de ``Payment``, sem depender de ``GET /v1/payments``.

.. deprecated:: 2.11.0-r4-f8
    ``_upsert`` resolvia o ``CoreBooking``/``company_id`` via join com
    ``Agendamento`` legado (``payment.agendamento_id``). A tabela
    ``agendamentos`` foi removida (DROP físico — ADR-024 sunset / RFC-003
    M11+) — resolve o booking diretamente via ``payment.booking_id``
    (bridge R4-F6, path preferencial) ou, em fallback, via
    ``CoreBooking.legacy_agendamento_id == payment.agendamento_id``
    (coluna inteira simples, sem depender da tabela removida).
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.payments.models import (
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
    # processando → pending: CorePayment não tem status equivalente.
    # EffectivePaidSnapshot lê processando só em Payment; item separado
    # se for necessário espelhar processing no Core.
    PaymentStatus.PROCESSANDO: CorePaymentStatus.PENDING,
    PaymentStatus.PAID: CorePaymentStatus.PAID,
    PaymentStatus.PAGO: CorePaymentStatus.PAID,
    PaymentStatus.FAILED: CorePaymentStatus.FAILED,
    PaymentStatus.CANCELADO: CorePaymentStatus.FAILED,
    PaymentStatus.REFUNDED: CorePaymentStatus.REFUNDED,
    PaymentStatus.REEMBOLSADO: CorePaymentStatus.REFUNDED,
}


class PaymentLegacySyncService:
    """
    Espelha ``Payment`` em ``CorePayment`` (Strangler Fig).

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_payment(
        self, payment: Payment, *, commit: bool = False
    ) -> Optional[CorePayment]:
        """
        Sincroniza um ``Payment`` já persistido (ou flushed) para ``CorePayment``.

        Idempotente via ``legacy_payment_id``. Não cria ``Payment``, não altera
        ``deposit_paid`` e não decide ativação/expiração. Preferir
        ``commit=False`` quando o caller já controla a transação do writer.

        Args:
            payment: Registro ``payments`` com ``id`` atribuído.
            commit: Se ``True``, faz ``commit`` ao final; se ``False``, apenas
                ``flush`` (mesmo commit do writer).

        Returns:
            ``CorePayment`` criado/atualizado, ou ``None`` se o booking/tenant
            não puder ser resolvido com segurança.
        """
        if payment is None or getattr(payment, "id", None) is None:
            logger.warning(
                "sync_payment ignorado — Payment sem id (flush necessário antes)"
            )
            return None

        row = self._upsert(payment)
        if commit:
            self.db.commit()
            if row is not None:
                self.db.refresh(row)
        else:
            self.db.flush()
        return row

    def sync_all(self) -> int:
        """
        Sincroniza todos os payments ativos (bootstrap / GET legado).

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
        Sincroniza um payment por id (inclui soft-deleted para espelhar delete).

        Args:
            payment_id: ID ``payments``.

        Returns:
            CorePayment ou None.
        """
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return None
        return self.sync_payment(payment, commit=True)

    def _upsert(self, payment: Payment) -> Optional[CorePayment]:
        """
        Cria ou atualiza ``core_payments`` a partir de ``Payment``.

        Resolve o booking via ``payment.booking_id`` (preferencial) ou
        ``legacy_agendamento_id``. Sem booking/tenant, não cria espelho.

        Soft-delete: se ``Payment.deleted_at`` estiver preenchido, atualiza o
        espelho existente e **não** cria CorePayment novo.

        Args:
            payment: Registro legado.

        Returns:
            CorePayment ou None se nenhum booking puder ser resolvido.
        """
        booking = self._resolve_booking(payment)
        if not booking:
            logger.warning(
                "sync Payment.id=%s ignorado — booking/tenant irresolvível "
                "(booking_id=%s agendamento_id=%s)",
                payment.id,
                payment.booking_id,
                payment.agendamento_id,
            )
            return None

        if booking.company_id is None:
            logger.warning(
                "sync Payment.id=%s ignorado — booking.id=%s sem company_id",
                payment.id,
                booking.id,
            )
            return None

        existing = (
            self.db.query(CorePayment)
            .filter(CorePayment.legacy_payment_id == payment.id)
            .first()
        )

        # Soft-delete: não ressuscita nem cria espelho novo a partir de deletado.
        if payment.deleted_at is not None:
            if existing is None:
                return None
            existing.deleted_at = payment.deleted_at
            existing.booking_id = booking.id
            existing.company_id = int(booking.company_id)
            return existing

        ptype = _TYPE_MAP.get(payment.tipo, CorePaymentType.DEPOSIT)
        pstatus = _STATUS_MAP.get(payment.status, CorePaymentStatus.PENDING)

        payload = dict(
            company_id=int(booking.company_id),
            booking_id=booking.id,
            payment_type=ptype,
            amount=Decimal(str(payment.valor)),
            status=pstatus,
            transaction_id=payment.transaction_id,
            receipt_url=payment.comprovante_url,
            paid_at=payment.paid_at,
            legacy_agendamento_id=payment.agendamento_id,
            deleted_at=None,
        )

        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing

        row = CorePayment(legacy_payment_id=payment.id, **payload)
        try:
            # Savepoint: IntegrityError não derruba a transação do writer.
            with self.db.begin_nested():
                self.db.add(row)
                self.db.flush()
            return row
        except IntegrityError:
            # Race: outro worker criou o espelho com o mesmo legacy_payment_id.
            existing = (
                self.db.query(CorePayment)
                .filter(CorePayment.legacy_payment_id == payment.id)
                .first()
            )
            if existing is None:
                logger.warning(
                    "IntegrityError no sync Payment.id=%s sem linha recuperável",
                    payment.id,
                    exc_info=True,
                )
                return None
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing

    def _resolve_booking(self, payment: Payment) -> Optional[CoreBooking]:
        """
        Resolve o ``CoreBooking`` dono do Payment para derivar ``company_id``.

        Args:
            payment: Registro ``payments``.

        Returns:
            CoreBooking ou None.
        """
        if payment.booking_id:
            return (
                self.db.query(CoreBooking)
                .filter(CoreBooking.id == payment.booking_id)
                .first()
            )
        if payment.agendamento_id:
            return (
                self.db.query(CoreBooking)
                .filter(
                    CoreBooking.legacy_agendamento_id == payment.agendamento_id
                )
                .first()
            )
        return None
