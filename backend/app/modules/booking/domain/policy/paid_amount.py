"""
Apuração do valor efetivamente pago (RECONCILE-DEPOSIT-SOURCES-01).

Fonte canônica: ledger ``Payment`` / ``CorePayment`` (não o snapshot
``CoreBooking.deposit_amount``). Anti-dupla Strangler:
``max(soma_payments, soma_core_payments)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

from sqlalchemy.orm import Session

from app.modules.booking.domain.policy.activation import money_to_cents


@dataclass(frozen=True)
class EffectivePaidSnapshot:
    """
    Snapshot do valor pago efetivo de um booking.

    Attributes:
        paid_cents: Centavos pagos válidos (não negativo).
        has_processing: Há pagamento ``processando`` (fail-closed no expirador).
        has_paid_rows: Existe ao menos uma linha com status pago contabilizada.
    """

    paid_cents: int
    has_processing: bool
    has_paid_rows: bool


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


def load_effective_paid_snapshots(
    db: Session,
    booking_ids: Sequence[int],
    *,
    company_id: Optional[int] = None,
) -> Dict[int, EffectivePaidSnapshot]:
    """
    Carrega o valor efetivamente pago por booking a partir do ledger.

    Política de pagamentos válidos (somente estes somam):

    - ``Payment.status`` ∈ {``paid``, ``pago``};
    - ``CorePayment.status`` = ``paid``;
    - ``deleted_at IS NULL``;
    - tipos de estorno (``refund`` / ``reembolso``) excluídos da soma;
    - ``processando`` não soma, mas marca ``has_processing``.

    Anti-dupla entre tabelas: ``paid_cents = max(soma_Payment, soma_CorePayment)``.
    Quando ``company_id`` é informado, ``CorePayment`` é filtrado por tenant e
    ``Payment`` só entra se o ``booking_id`` pertencer a esse tenant
    (via ``CoreBooking.company_id``).

    Args:
        db: Sessão SQLAlchemy.
        booking_ids: IDs ``core_bookings.id``.
        company_id: Tenant efetivo (recomendado; filtra CorePayment e valida Payment).

    Returns:
        Mapa ``booking_id → EffectivePaidSnapshot``.

    Raises:
        Exception: Propagada ao caller (expirador aplica fail-closed).
    """
    from app.models.payment import Payment, PaymentStatus, PaymentType
    from app.modules.booking.domain.models import CoreBooking
    from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType

    ids = [int(b) for b in booking_ids if b is not None]
    empty = {
        bid: EffectivePaidSnapshot(paid_cents=0, has_processing=False, has_paid_rows=False)
        for bid in ids
    }
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
        empty = {
            bid: EffectivePaidSnapshot(
                paid_cents=0, has_processing=False, has_paid_rows=False
            )
            for bid in allowed_ids
        }
        if not allowed_ids:
            return {}

    paid_payments: Dict[int, int] = {bid: 0 for bid in allowed_ids}
    paid_core: Dict[int, int] = {bid: 0 for bid in allowed_ids}
    processing: Dict[int, bool] = {bid: False for bid in allowed_ids}
    has_paid: Dict[int, bool] = {bid: False for bid in allowed_ids}

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
        has_paid[bid] = True

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
        has_paid[bid] = True

    result: Dict[int, EffectivePaidSnapshot] = {}
    for bid in allowed_ids:
        paid = max(int(paid_payments[bid]), int(paid_core[bid]))
        result[bid] = EffectivePaidSnapshot(
            paid_cents=paid,
            has_processing=bool(processing[bid]),
            has_paid_rows=bool(has_paid[bid]),
        )
    # Inclui ids pedidos mas fora do tenant como zero explícito (não vaza dados).
    for bid in ids:
        if bid not in result:
            result[bid] = EffectivePaidSnapshot(
                paid_cents=0, has_processing=False, has_paid_rows=False
            )
    return result


def get_effective_paid_amount_cents(
    db: Session,
    *,
    booking_id: int,
    company_id: int,
) -> int:
    """
    Retorna o valor efetivamente pago de um booking em centavos.

    Args:
        db: Sessão SQLAlchemy.
        booking_id: ID ``core_bookings.id``.
        company_id: Tenant efetivo.

    Returns:
        Centavos >= 0 segundo a política canônica do ledger.
    """
    snap = load_effective_paid_snapshots(
        db, [int(booking_id)], company_id=int(company_id)
    ).get(int(booking_id))
    if snap is None:
        return 0
    return int(snap.paid_cents)


def snapshots_as_dicts(
    snapshots: Dict[int, EffectivePaidSnapshot],
) -> Dict[int, Dict[str, Any]]:
    """
    Converte snapshots tipados para o formato legado do expirador.

    Args:
        snapshots: Mapa tipado.

    Returns:
        Mapa ``booking_id → {paid_cents, has_processing, has_paid_rows}``.
    """
    return {
        bid: {
            "paid_cents": int(s.paid_cents),
            "has_processing": bool(s.has_processing),
            "has_paid_rows": bool(s.has_paid_rows),
        }
        for bid, s in snapshots.items()
    }
