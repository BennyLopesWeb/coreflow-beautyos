"""
Service de pagamentos persistidos (sinal e final).
"""
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.services.financeiro_service import FinanceiroService


class PaymentReservationService:
    """
    Gerencia pagamentos DEPOSIT e FINAL_PAYMENT persistidos na tabela payments.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db
        self.financeiro = FinanceiroService(db)

    def criar_pendente(
        self,
        agendamento_id: int,
        tipo: PaymentType,
        valor: Decimal,
    ) -> Payment:
        """
        Cria registro de pagamento pendente.

        Args:
            agendamento_id: ID da reserva.
            tipo: DEPOSIT ou FINAL_PAYMENT.
            valor: Valor do pagamento.

        Returns:
            Payment persistido.
        """
        pag = Payment(
            agendamento_id=agendamento_id,
            tipo=tipo,
            valor=valor,
            status=PaymentStatus.PENDING,
        )
        self.db.add(pag)
        self.db.commit()
        self.db.refresh(pag)
        return pag

    def confirmar_deposito(
        self,
        agendamento_id: int,
        transaction_id: Optional[str] = None,
        comprovante_url: Optional[str] = None,
    ) -> Payment:
        """
        Confirma pagamento do sinal e atualiza reserva.

        Args:
            agendamento_id: ID da reserva.
            transaction_id: ID externo opcional.
            comprovante_url: URL do comprovante.

        Returns:
            Payment confirmado.
        """
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        if not ag:
            raise NotFoundError("Reserva", str(agendamento_id))

        pag = (
            self.db.query(Payment)
            .filter(
                Payment.agendamento_id == agendamento_id,
                Payment.tipo.in_([PaymentType.DEPOSIT, PaymentType.SINAL]),
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.PENDENTE]),
            )
            .first()
        )
        if not pag:
            pag = Payment(
                agendamento_id=agendamento_id,
                tipo=PaymentType.DEPOSIT,
                valor=ag.valor_sinal,
                status=PaymentStatus.PENDING,
            )
            self.db.add(pag)

        pag.status = PaymentStatus.PAID
        pag.transaction_id = transaction_id
        pag.comprovante_url = comprovante_url or ag.comprovante_url
        pag.paid_at = datetime.utcnow()

        ag.sinal_pago = True
        ag.status = ReservationStatus.PENDING_APPROVAL
        ag.status_pagamento = StatusPagamento.PARTIALLY_PAID
        if comprovante_url:
            ag.comprovante_url = comprovante_url

        self.db.commit()
        self.db.refresh(pag)

        self.financeiro.registrar_entrada_automatica(
            descricao=f"Sinal - Reserva #{ag.id}",
            valor=ag.valor_sinal,
            agendamento_id=ag.id,
        )

        self._sync_core_booking_deposit(ag.id)

        from app.modules.booking.domain.events import DEPOSIT_CONFIRMED
        from app.modules.payments.application.legacy_sync_service import PaymentLegacySyncService
        from app.shared.events.outbox import OutboxService
        from app.shared.events.domain_event import DomainEvent

        PaymentLegacySyncService(self.db).sync_one(pag.id)

        if ag.company_id:
            OutboxService(self.db).record_and_publish(
                DomainEvent(
                    event_type=DEPOSIT_CONFIRMED,
                    company_id=ag.company_id,
                    aggregate_id=str(pag.id),
                    aggregate_type="Payment",
                    payload={
                        "payment_id": pag.id,
                        "agendamento_id": ag.id,
                        "amount": str(ag.valor_sinal),
                    },
                )
            )
            self.db.commit()

        return pag

    def _sync_core_booking_deposit(self, agendamento_id: int) -> None:
        """
        Sincroniza ``CoreBooking.deposit_paid`` a partir do sinal legado (R4-F2).

        Nice-to-have de paridade: quando o booking core está vinculado a um
        ``Agendamento`` via ``legacy_agendamento_id`` (flag de projeção ON),
        confirmar o sinal legado também deve refletir no core, para que
        ``PaymentQueryPort.is_deposit_confirmed`` (que lê ``deposit_paid``
        direto do core) fique consistente independente do caminho usado.

        Args:
            agendamento_id: ID ``agendamentos.id`` cujo sinal foi confirmado.

        Returns:
            None
        """
        from app.modules.booking.domain.models import CoreBooking

        core = (
            self.db.query(CoreBooking)
            .filter(CoreBooking.legacy_agendamento_id == agendamento_id)
            .first()
        )
        if core and not core.deposit_paid:
            core.deposit_paid = True
            self.db.commit()

    def confirmar_deposito_por_booking(self, booking_id: int) -> "CoreBooking":
        """
        Confirma sinal diretamente em booking core-only, sem ``Agendamento`` (R4-F2/R4-F3).

        Path usado sempre desde R4-F3 (dual-write outbound removido
        definitivamente): não existe projeção legado (``agendamentos``/
        ``payments``) para o booking, então a confirmação do sinal atualiza
        ``CoreBooking.deposit_paid`` diretamente — é isso que
        ``PaymentQueryPort.is_deposit_confirmed`` consulta para liberar o
        approve (ADR-028).

        Args:
            booking_id: ID ``core_bookings.id``.

        Returns:
            CoreBooking atualizado com ``deposit_paid=True``.

        Raises:
            NotFoundError: Booking não encontrado.
        """
        from app.modules.booking.domain.models import CoreBooking
        from app.models.agendamento import StatusPagamento as _StatusPagamento

        row = self.db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
        if not row:
            raise NotFoundError("Booking", str(booking_id))

        row.deposit_paid = True
        row.payment_status = _StatusPagamento.PARTIALLY_PAID
        self.db.commit()
        self.db.refresh(row)
        return row

    def confirmar_pagamento_final(
        self,
        agendamento_id: int,
        transaction_id: Optional[str] = None,
    ) -> Payment:
        """
        Confirma pagamento do valor restante.

        Args:
            agendamento_id: ID da reserva.
            transaction_id: ID externo opcional.

        Returns:
            Payment confirmado.
        """
        ag = self.db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        if not ag:
            raise NotFoundError("Reserva", str(agendamento_id))
        if ag.status not in (
            ReservationStatus.COMPLETED,
            ReservationStatus.CONCLUIDO,
        ):
            raise BusinessRuleError("Reserva deve estar concluída para pagamento final")

        pag = Payment(
            agendamento_id=agendamento_id,
            tipo=PaymentType.FINAL_PAYMENT,
            valor=ag.valor_restante,
            status=PaymentStatus.PAID,
            transaction_id=transaction_id,
            paid_at=datetime.utcnow(),
        )
        self.db.add(pag)

        ag.status = ReservationStatus.PAID
        ag.status_pagamento = StatusPagamento.PAID

        self.db.commit()
        self.db.refresh(pag)

        self.financeiro.registrar_entrada_automatica(
            descricao=f"Pagamento final - Reserva #{ag.id}",
            valor=ag.valor_restante,
            agendamento_id=ag.id,
        )
        return pag

    def listar_por_reserva(self, agendamento_id: int) -> List[Payment]:
        """
        Lista pagamentos de uma reserva.

        Args:
            agendamento_id: ID da reserva.

        Returns:
            Lista de Payment.
        """
        return (
            self.db.query(Payment)
            .filter(Payment.agendamento_id == agendamento_id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at)
            .all()
        )
