"""
Service de pagamentos persistidos (sinal e final).
"""
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.core.exceptions import (
    NotFoundError,
    BusinessRuleError,
    ConflictError,
    MinimumDepositNotMetError,
    ValidationError,
)
from app.core.logging_config import get_logger
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    money_to_cents,
)
from app.modules.booking.domain.policy.paid_amount import (
    get_effective_paid_snapshot,
)
from app.services.financeiro_service import FinanceiroService

logger = get_logger("payment_reservation_service")

# Status de booking/pagamento que bloqueiam confirmação financeira (FIX-04).
_BOOKING_STATUS_BLOQUEADOS = frozenset(
    {
        ReservationStatus.CANCELLED,
        ReservationStatus.CANCELADO,
    }
)
_PAYMENT_STATUS_BLOQUEADOS = frozenset(
    {
        StatusPagamento.CANCELLED,
    }
)


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
        agendamento_id: Optional[int],
        tipo: PaymentType,
        valor: Decimal,
        booking_id: Optional[int] = None,
    ) -> Payment:
        """
        Cria registro de pagamento pendente.

        R4-F6 (bridge Payment→booking_id): ``agendamento_id`` pode ser
        ``None`` desde que ``booking_id`` seja informado — caso de
        pagamentos para bookings core-only (sem ``Agendamento`` associado).
        Ao menos um dos dois deve estar presente.

        Args:
            agendamento_id: ID da reserva legado (``agendamentos.id``), ou
                ``None`` para bookings core-only.
            tipo: DEPOSIT ou FINAL_PAYMENT.
            valor: Valor do pagamento.
            booking_id: ID ``core_bookings.id`` (R4-F6). Obrigatório quando
                ``agendamento_id`` é ``None``.

        Returns:
            Payment persistido.

        Raises:
            BusinessRuleError: Se ``agendamento_id`` e ``booking_id`` forem
                ambos ``None``.
        """
        if agendamento_id is None and booking_id is None:
            raise BusinessRuleError(
                "Informe agendamento_id (legado) ou booking_id (core) para criar o pagamento"
            )
        pag = Payment(
            agendamento_id=agendamento_id,
            booking_id=booking_id,
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
        Confirma pagamento do sinal de uma reserva legado.

        .. deprecated:: 2.11.0-r4-f8
            A tabela ``agendamentos`` foi removida (DROP físico — ADR-024
            sunset / RFC-003 M11+). Sempre levanta ``NotFoundError``. Use
            ``confirmar_deposito_por_booking`` (path core-only, único
            desde R4-F6).

        Args:
            agendamento_id: ID da reserva legado.
            transaction_id: Ignorado.
            comprovante_url: Ignorado.

        Raises:
            NotFoundError: Sempre — a tabela não existe mais.
        """
        raise NotFoundError("Reserva", str(agendamento_id))

    def _obter_booking_do_tenant(
        self, booking_id: int, company_id: int
    ) -> "CoreBooking":
        """
        Busca ``CoreBooking`` por PK e ``company_id`` na mesma query SQL.

        FIX-04: o filtro de tenant ocorre no SQL (não em memória), para
        impedir mutação financeira cross-tenant e não distinguir
        "inexistente" de "outro tenant" na mensagem de erro.

        Args:
            booking_id: ID ``core_bookings.id``.
            company_id: Tenant efetivo do admin (obrigatório).

        Returns:
            CoreBooking do tenant.

        Raises:
            NotFoundError: Booking inexistente ou de outro tenant (404 genérico).
        """
        from app.modules.booking.domain.models import CoreBooking

        row = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.company_id == company_id,
            )
            .first()
        )
        if not row:
            raise NotFoundError("Booking")
        return row

    def _assert_booking_confirmavel(self, booking: "CoreBooking") -> None:
        """
        Bloqueia confirmação financeira em booking cancelado/estornado (FIX-04).

        Args:
            booking: ``CoreBooking`` já filtrado pelo tenant.

        Raises:
            ConflictError: Status de reserva ou pagamento impede confirmação (409).
        """
        status_val = booking.status
        if status_val in _BOOKING_STATUS_BLOQUEADOS:
            raise ConflictError(
                "Booking cancelado ou estornado não pode ter pagamento confirmado"
            )
        pay_val = booking.payment_status
        if pay_val in _PAYMENT_STATUS_BLOQUEADOS:
            raise ConflictError(
                "Booking cancelado ou estornado não pode ter pagamento confirmado"
            )

    def _assert_minimum_activation_met(
        self, booking: "CoreBooking", *, company_id: int
    ) -> None:
        """
        Garante que o ledger reconciliado atinge o mínimo de ativação.

        ``deposit_amount`` do booking é cotação comercial e **não** entra
        nesta apuração. Fail-closed se a consulta financeira falhar, se
        houver ``processando``, ou se ``Payment`` e ``CorePayment``
        divergirem materialmente.

        Args:
            booking: ``CoreBooking`` candidato à ativação.
            company_id: Tenant efetivo.

        Raises:
            ValidationError: Total inválido, falha de consulta, processing
                ou divergência de fontes.
            MinimumDepositNotMetError: Ledger reconciliado abaixo do mínimo.
        """
        total_cents = money_to_cents(booking.price_total)
        if total_cents is None or total_cents <= 0:
            raise ValidationError(
                "Não é possível ativar a reserva: preço total inválido."
            )
        from app.modules.booking.domain.policy.activation import (
            resolve_booking_minimum_activation_cents,
        )

        try:
            minimum = resolve_booking_minimum_activation_cents(booking)
        except ValueError as exc:
            raise ValidationError(
                "Não é possível ativar a reserva: preço total inválido."
            ) from exc
        try:
            snap = get_effective_paid_snapshot(
                self.db,
                booking_id=int(booking.id),
                company_id=int(company_id),
            )
        except Exception as exc:
            logger.warning(
                "Falha ao apurar ledger booking_id=%s company_id=%s — "
                "ativação bloqueada (fail-closed)",
                booking.id,
                company_id,
                exc_info=True,
            )
            raise ValidationError(
                "Não foi possível consultar o ledger financeiro para ativação."
            ) from exc

        if snap.has_processing:
            raise ValidationError(
                "Há pagamento em processamento; a reserva não pode ser ativada."
            )
        if snap.has_source_divergence or not snap.is_reconciled:
            raise ValidationError(
                "Divergência entre Payment e CorePayment; ativação bloqueada "
                "para análise manual."
            )
        if snap.paid_cents < minimum:
            raise MinimumDepositNotMetError(minimum)

    def confirmar_deposito_por_booking(
        self, booking_id: int, company_id: int
    ) -> "CoreBooking":
        """
        Confirma sinal em booking core-only quando o ledger já cobre o mínimo.

        Path preferencial desde R4-F3 / R4-F6: atualiza
        ``CoreBooking.deposit_paid`` (consulta de approve, ADR-028).

        RECONCILE-DEPOSIT-SOURCES-01 — semântica explícita:

        - ``deposit_amount`` = cotação comercial do sinal (não é pagamento);
        - este endpoint **não** registra recebimento manual nem faz upsert
          de ``Payment`` a partir do snapshot;
        - apenas confirma pagamentos **já existentes** no ledger
          (``Payment`` / ``CorePayment``) se reconciliados e >= mínimo.

        R4-F9: na primeira confirmação bem-sucedida, registra entrada em
        ``Financeiro`` (best-effort; falha não reverte ``deposit_paid``).

        FIX-04: exige ``company_id``; bloqueia cancelado/estornado (409);
        se ``deposit_paid`` já for ``True``, retorna sem efeitos colaterais.

        Args:
            booking_id: ID ``core_bookings.id``.
            company_id: Tenant efetivo (``CoreBooking.company_id``).

        Returns:
            CoreBooking atualizado com ``deposit_paid=True`` (ou já pago).

        Raises:
            NotFoundError: Booking não encontrado neste tenant.
            ConflictError: Booking cancelado/estornado.
            ValidationError: Total inválido, falha de ledger, processing ou
                divergência de fontes.
            MinimumDepositNotMetError: Ledger abaixo do mínimo (valores
                permanecem para análise manual; booking não ativa).
        """
        row = self._obter_booking_do_tenant(booking_id, company_id)
        self._assert_booking_confirmavel(row)

        # Idempotência (FIX-04): estado alvo já atingido — sem efeitos colaterais.
        if bool(row.deposit_paid):
            return row

        self._assert_minimum_activation_met(row, company_id=company_id)

        row.deposit_paid = True
        row.payment_status = StatusPagamento.PARTIALLY_PAID

        self.db.commit()
        self.db.refresh(row)

        # R4-F9 — paridade contábil: entrada Financeiro na 1ª confirmação
        try:
            self.financeiro.registrar_entrada_automatica(
                descricao=f"Sinal - Booking #{booking_id}",
                valor=Decimal(str(row.deposit_amount or 0)),
                agendamento_id=row.legacy_agendamento_id,
            )
        except Exception:
            logger.exception(
                "Falha ao registrar entrada Financeiro para booking_id=%s (best-effort)",
                booking_id,
            )

        self.db.refresh(row)
        return row

    def confirmar_pagamento_final(
        self,
        agendamento_id: int,
        transaction_id: Optional[str] = None,
    ) -> Payment:
        """
        Confirma pagamento do valor restante de uma reserva legado.

        .. deprecated:: 2.11.0-r4-f8
            A tabela ``agendamentos`` foi removida (DROP físico — ADR-024
            sunset / RFC-003 M11+). Sempre levanta ``NotFoundError``.
            Use ``confirmar_pagamento_final_por_booking`` (R4-F10).

        Args:
            agendamento_id: ID da reserva legado.
            transaction_id: Ignorado.

        Raises:
            NotFoundError: Sempre — a tabela não existe mais.
        """
        raise NotFoundError("Reserva", str(agendamento_id))

    def confirmar_pagamento_final_por_booking(
        self, booking_id: int, company_id: int
    ) -> "CoreBooking":
        """
        Confirma pagamento final (remaining) em booking core-only (R4-F10).

        Path único de escrita de pagamento final pós-DROP ``agendamentos``:
        atualiza ``CoreBooking.payment_status`` para ``PAID``, cria/atualiza
        ``Payment`` tipo ``FINAL_PAYMENT`` vinculado por ``booking_id`` e
        registra entrada ``Financeiro`` na primeira confirmação (best-effort,
        espelhando R4-F9 no deposit).

        FIX-04: exige ``company_id`` e filtra na query SQL; bloqueia
        cancelado/estornado (409); se já ``PAID``, retorna sem reprocessar
        Payment nem Financeiro. A regra "final sem sinal" permanece após
        os gates de tenant e status.

        Args:
            booking_id: ID ``core_bookings.id``.
            company_id: Tenant efetivo (``CoreBooking.company_id``).

        Returns:
            CoreBooking atualizado com ``payment_status=PAID`` (ou já pago).

        Raises:
            NotFoundError: Booking não encontrado neste tenant.
            ConflictError: Booking cancelado/estornado.
            BusinessRuleError: Sinal ainda não confirmado (``deposit_paid``).
        """
        row = self._obter_booking_do_tenant(booking_id, company_id)
        self._assert_booking_confirmavel(row)

        if not row.deposit_paid:
            raise BusinessRuleError(
                "Confirme o sinal antes do pagamento final "
                f"(booking_id={booking_id})"
            )

        # Idempotência (FIX-04): estado alvo já atingido — sem efeitos colaterais.
        if row.payment_status == StatusPagamento.PAID:
            return row

        row.payment_status = StatusPagamento.PAID
        self._upsert_payment_final_por_booking(row)

        self.db.commit()
        self.db.refresh(row)

        try:
            self.financeiro.registrar_entrada_automatica(
                descricao=f"Pagamento final - Booking #{booking_id}",
                valor=Decimal(str(row.remaining_amount or 0)),
                agendamento_id=row.legacy_agendamento_id,
            )
        except Exception:
            logger.exception(
                "Falha ao registrar Financeiro (final) booking_id=%s (best-effort)",
                booking_id,
            )

        self.db.refresh(row)
        return row

    def _upsert_payment_final_por_booking(self, booking) -> Optional[Payment]:
        """
        Cria ou atualiza ``Payment`` FINAL_PAYMENT vinculado a ``CoreBooking``.

        Best-effort de auditoria (R4-F10): erros não interrompem a
        confirmação — a fonte de verdade é ``CoreBooking.payment_status``.

        Args:
            booking: ``CoreBooking`` com ``payment_status`` já marcado ``PAID``.

        Returns:
            Payment persistido, ou ``None`` se falha ser não fatal.
        """
        try:
            pag = (
                self.db.query(Payment)
                .filter(
                    Payment.booking_id == booking.id,
                    Payment.tipo.in_([PaymentType.FINAL_PAYMENT, PaymentType.FINAL]),
                )
                .first()
            )
            if not pag:
                pag = Payment(
                    booking_id=booking.id,
                    agendamento_id=booking.legacy_agendamento_id,
                    tipo=PaymentType.FINAL_PAYMENT,
                    valor=booking.remaining_amount,
                    status=PaymentStatus.PENDING,
                )
                self.db.add(pag)

            pag.status = PaymentStatus.PAID
            pag.paid_at = datetime.utcnow()
            return pag
        except Exception:
            logger.warning(
                "Falha não fatal ao sincronizar Payment FINAL booking_id=%s (R4-F10)",
                booking.id,
                exc_info=True,
            )
            return None

    def listar_por_reserva(self, agendamento_id: int) -> List[Payment]:
        """
        Lista pagamentos de uma reserva legado (coluna histórica).

        Args:
            agendamento_id: ID legado em ``payments.agendamento_id``.

        Returns:
            Lista de Payment.
        """
        return (
            self.db.query(Payment)
            .filter(Payment.agendamento_id == agendamento_id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at)
            .all()
        )

    def listar_por_booking(self, booking_id: int) -> List[Payment]:
        """
        Lista pagamentos vinculados a um ``core_bookings.id`` (R4-F10).

        Args:
            booking_id: ID ``core_bookings.id``.

        Returns:
            Lista de Payment ordenada por criação.
        """
        return (
            self.db.query(Payment)
            .filter(Payment.booking_id == booking_id, Payment.deleted_at.is_(None))
            .order_by(Payment.created_at)
            .all()
        )
