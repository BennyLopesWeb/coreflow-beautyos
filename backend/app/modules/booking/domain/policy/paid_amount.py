"""
Apuração do valor efetivamente pago (RECONCILE-DEPOSIT-SOURCES-01).

``CoreBooking.deposit_amount`` é cotação comercial — **não** é pagamento.

Fonte financeira: ledger ``Payment`` / ``CorePayment``. O ``max`` entre
somas é apenas mitigação temporária Strangler e **nunca** oculta
divergência material (ambas as fontes com valor e valores diferentes).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from sqlalchemy.orm import Session

from app.modules.booking.domain.policy.activation import money_to_cents

# Domínio atual não persiste moeda por pagamento; padrão BRL.
DEFAULT_CURRENCY = "BRL"


@dataclass(frozen=True)
class EffectivePaidSnapshot:
    """
    Snapshot de reconciliação financeira de um booking.

    Attributes:
        paid_cents: Valor considerado para comparação com o mínimo quando
            a apuração está reconciliada (fonte única ou fontes iguais).
            Em divergência, espelha ``max`` apenas informativo — a ativação
            e a expiração devem bloquear via ``has_source_divergence``.
        payment_cents: Soma válida em ``Payment``.
        core_payment_cents: Soma válida em ``CorePayment``.
        source_used: ``none`` | ``payment`` | ``core_payment`` | ``both``.
        has_processing: Há ``processando`` (não conta como pago).
        has_paid_rows: Há ao menos uma linha paga contabilizada.
        has_source_divergence: Ambas as fontes com valor e valores diferentes.
        is_reconciled: Sem divergência material (seguro para decisão automática).
        currency: Moeda ISO (hoje sempre BRL).
    """

    paid_cents: int
    payment_cents: int
    core_payment_cents: int
    source_used: str
    has_processing: bool
    has_paid_rows: bool
    has_source_divergence: bool
    is_reconciled: bool
    currency: str = DEFAULT_CURRENCY


def _status_value(status: Any) -> str:
    """
    Normaliza enum/string de status para comparação.

    Args:
        status: Enum com ``.value`` ou valor bruto.

    Returns:
        String do status.
    """
    return status.value if hasattr(status, "value") else str(status)


def _type_value(tipo: Any) -> str:
    """
    Normaliza enum/string de tipo de pagamento.

    Args:
        tipo: Enum com ``.value`` ou valor bruto.

    Returns:
        String do tipo.
    """
    return tipo.value if hasattr(tipo, "value") else str(tipo)


def _empty_snapshot() -> EffectivePaidSnapshot:
    """
    Snapshot zerado (sem linhas / booking fora do tenant).

    Returns:
        ``EffectivePaidSnapshot`` reconciliado com zeros.
    """
    return EffectivePaidSnapshot(
        paid_cents=0,
        payment_cents=0,
        core_payment_cents=0,
        source_used="none",
        has_processing=False,
        has_paid_rows=False,
        has_source_divergence=False,
        is_reconciled=True,
        currency=DEFAULT_CURRENCY,
    )


def _build_snapshot(
    *,
    payment_cents: int,
    core_cents: int,
    has_processing: bool,
) -> EffectivePaidSnapshot:
    """
    Monta o snapshot de reconciliação a partir das somas por fonte.

    Args:
        payment_cents: Soma ``Payment``.
        core_cents: Soma ``CorePayment``.
        has_processing: Flag de processamento.

    Returns:
        Snapshot com ``source_used``, divergência e ``paid_cents``.
    """
    payment_cents = int(payment_cents)
    core_cents = int(core_cents)
    has_paid = payment_cents > 0 or core_cents > 0

    if payment_cents > 0 and core_cents > 0 and payment_cents != core_cents:
        return EffectivePaidSnapshot(
            paid_cents=max(payment_cents, core_cents),
            payment_cents=payment_cents,
            core_payment_cents=core_cents,
            source_used="both",
            has_processing=bool(has_processing),
            has_paid_rows=True,
            has_source_divergence=True,
            is_reconciled=False,
            currency=DEFAULT_CURRENCY,
        )

    if payment_cents > 0 and core_cents > 0:
        source_used = "both"
        paid = payment_cents
    elif payment_cents > 0:
        source_used = "payment"
        paid = payment_cents
    elif core_cents > 0:
        source_used = "core_payment"
        paid = core_cents
    else:
        source_used = "none"
        paid = 0

    return EffectivePaidSnapshot(
        paid_cents=paid,
        payment_cents=payment_cents,
        core_payment_cents=core_cents,
        source_used=source_used,
        has_processing=bool(has_processing),
        has_paid_rows=has_paid,
        has_source_divergence=False,
        is_reconciled=True,
        currency=DEFAULT_CURRENCY,
    )


def load_effective_paid_snapshots(
    db: Session,
    booking_ids: Sequence[int],
    *,
    company_id: Optional[int] = None,
) -> Dict[int, EffectivePaidSnapshot]:
    """
    Carrega snapshots de reconciliação financeira por booking.

    Política de pagamentos válidos (somente estes somam):

    - ``Payment.status`` ∈ {``paid``, ``pago``};
    - ``CorePayment.status`` = ``paid``;
    - ``deleted_at IS NULL``;
    - tipos de estorno (``refund`` / ``reembolso``) excluídos;
    - ``processando`` não soma; marca ``has_processing``.

    Divergência material: ambas as fontes com valor ``> 0`` e valores
    diferentes → ``has_source_divergence=True``, ``is_reconciled=False``.

    Args:
        db: Sessão SQLAlchemy.
        booking_ids: IDs ``core_bookings.id``.
        company_id: Tenant efetivo (filtra CorePayment e valida ownership).

    Returns:
        Mapa ``booking_id → EffectivePaidSnapshot``.

    Raises:
        Exception: Propagada ao caller (fail-closed na ativação/expiração).
    """
    from app.models.payment import Payment, PaymentStatus, PaymentType
    from app.modules.booking.domain.models import CoreBooking
    from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType

    ids = [int(b) for b in booking_ids if b is not None]
    if not ids:
        return {}

    allowed_ids = set(ids)
    if company_id is not None:
        owned = (
            db.query(CoreBooking.id)
            .filter(
                CoreBooking.id.in_(ids),
                CoreBooking.company_id == int(company_id),
            )
            .all()
        )
        allowed_ids = {int(r[0]) for r in owned}
        if not allowed_ids:
            return {bid: _empty_snapshot() for bid in ids}

    paid_payments: Dict[int, int] = {bid: 0 for bid in allowed_ids}
    paid_core: Dict[int, int] = {bid: 0 for bid in allowed_ids}
    processing: Dict[int, bool] = {bid: False for bid in allowed_ids}

    refund_types = {
        PaymentType.REFUND.value,
        PaymentType.REEMBOLSO.value,
    }
    payment_rows = (
        db.query(Payment)
        .filter(
            Payment.booking_id.in_(list(allowed_ids)),
            Payment.deleted_at.is_(None),
        )
        .all()
    )
    for row in payment_rows:
        if row.booking_id is None:
            continue
        bid = int(row.booking_id)
        if bid not in allowed_ids:
            continue
        status_val = _status_value(row.status)
        if status_val == PaymentStatus.PROCESSANDO.value:
            processing[bid] = True
            continue
        if status_val not in (PaymentStatus.PAID.value, PaymentStatus.PAGO.value):
            continue
        if _type_value(row.tipo) in refund_types:
            continue
        cents = money_to_cents(row.valor)
        if cents is None:
            continue
        paid_payments[bid] += cents

    core_q = db.query(CorePayment).filter(
        CorePayment.booking_id.in_(list(allowed_ids)),
        CorePayment.deleted_at.is_(None),
    )
    if company_id is not None:
        core_q = core_q.filter(CorePayment.company_id == int(company_id))
    for row in core_q.all():
        if row.booking_id is None:
            continue
        bid = int(row.booking_id)
        if bid not in allowed_ids:
            continue
        status_val = _status_value(row.status)
        if status_val != CorePaymentStatus.PAID.value:
            continue
        if _type_value(row.payment_type) == CorePaymentType.REFUND.value:
            continue
        cents = money_to_cents(row.amount)
        if cents is None:
            continue
        paid_core[bid] += cents

    result: Dict[int, EffectivePaidSnapshot] = {}
    for bid in allowed_ids:
        result[bid] = _build_snapshot(
            payment_cents=paid_payments[bid],
            core_cents=paid_core[bid],
            has_processing=processing[bid],
        )
    for bid in ids:
        if bid not in result:
            result[bid] = _empty_snapshot()
    return result


def get_effective_paid_snapshot(
    db: Session,
    *,
    booking_id: int,
    company_id: int,
) -> EffectivePaidSnapshot:
    """
    Retorna o snapshot de reconciliação de um booking.

    Args:
        db: Sessão SQLAlchemy.
        booking_id: ID ``core_bookings.id``.
        company_id: Tenant efetivo.

    Returns:
        ``EffectivePaidSnapshot`` (zerado se ausente).
    """
    snap = load_effective_paid_snapshots(
        db, [int(booking_id)], company_id=int(company_id)
    ).get(int(booking_id))
    return snap if snap is not None else _empty_snapshot()


def get_effective_paid_amount_cents(
    db: Session,
    *,
    booking_id: int,
    company_id: int,
) -> int:
    """
    Compatibilidade: retorna ``paid_cents`` do snapshot.

    Preferir ``get_effective_paid_snapshot`` para decisões de ativação /
    expiração (divergência / processing).

    Args:
        db: Sessão SQLAlchemy.
        booking_id: ID ``core_bookings.id``.
        company_id: Tenant efetivo.

    Returns:
        Centavos do campo ``paid_cents``.
    """
    return int(
        get_effective_paid_snapshot(
            db, booking_id=int(booking_id), company_id=int(company_id)
        ).paid_cents
    )


def snapshots_as_dicts(
    snapshots: Dict[int, EffectivePaidSnapshot],
) -> Dict[int, Dict[str, Any]]:
    """
    Converte snapshots tipados para dicts consumíveis pelo expirador.

    Args:
        snapshots: Mapa tipado.

    Returns:
        Mapa com todos os campos de reconciliação.
    """
    return {
        bid: {
            "paid_cents": int(s.paid_cents),
            "payment_cents": int(s.payment_cents),
            "core_payment_cents": int(s.core_payment_cents),
            "source_used": s.source_used,
            "has_processing": bool(s.has_processing),
            "has_paid_rows": bool(s.has_paid_rows),
            "has_source_divergence": bool(s.has_source_divergence),
            "is_reconciled": bool(s.is_reconciled),
            "currency": s.currency,
        }
        for bid, s in snapshots.items()
    }
