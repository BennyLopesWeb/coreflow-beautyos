"""
AUDIT-LEGACY-EVIDENCE-PENDING-01 — classificação read-only de evidências.

Após SEPARATE-PAYMENT-EVIDENCE-01 (PR #47), novos comprovantes gravam
``Payment.valor = 0.00``. Registros antigos podem ainda ter
``valor == booking.deposit_amount`` em status ``PENDING``.

Este módulo **não muta** dados: apenas classifica candidatos a um
possível backfill futuro (autorização separada).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


# Corte técnico: merge do PR #47 em main (UTC). Deploy operacional pode
# divergir; não usar sozinho para mutação automática.
PR47_MERGE_UTC = datetime(2026, 7, 29, 23, 22, 5, tzinfo=timezone.utc)
EVIDENCE_PLACEHOLDER = Decimal("0.00")

_PENDING = frozenset({"pending", "pendente"})
_PAID = frozenset({"paid", "pago"})
_DEPOSIT = frozenset({"deposit", "sinal"})
_FINAL = frozenset({"final_payment", "final"})
_REFUND = frozenset({"refund", "reembolso"})


class EvidenceClass(str, Enum):
    """
    Resultado da classificação de um ``Payment`` para auditoria de evidência.

    Attributes:
        CANDIDATE_BACKFILL: Critérios fortes de comprovante legado com cotação.
        ALREADY_CLEAN: Evidência já com placeholder ``0.00``.
        EXCLUDE_LEGITIMATE: Pagamento/financeiro que não deve ser alterado.
        REVIEW_REQUIRED: Ambíguo — exige revisão humana.
    """

    CANDIDATE_BACKFILL = "candidate_backfill"
    ALREADY_CLEAN = "already_clean"
    EXCLUDE_LEGITIMATE = "exclude_legitimate"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class EvidenceAuditInput:
    """
    Snapshot mínimo para classificação pura (sem ORM).

    Args:
        payment_id: ``payments.id``.
        status: Status do Payment (string/enum value).
        tipo: Tipo do Payment.
        valor: ``Payment.valor``.
        comprovante_url: URL de evidência, se houver.
        paid_at: Timestamp de liquidação, se houver.
        transaction_id: ID de transação financeira, se houver.
        deleted_at: Soft-delete do Payment.
        booking_id: FK ``core_bookings.id``.
        booking_company_id: Tenant do booking (None se irresolvível).
        booking_deposit_amount: Cotação do booking.
        booking_deposit_paid: Flag administrativa de sinal confirmado.
        booking_missing: True se ``booking_id`` não resolveu ``CoreBooking``.
        core_status: Status do CorePayment espelho (None se ausente).
        core_amount: Amount do espelho.
        core_paid_at: ``paid_at`` do espelho.
        core_transaction_id: Transação no espelho.
        core_receipt_url: Receipt no espelho.
        created_at: Criação do Payment (opcional; só sinal fraco).
    """

    payment_id: int
    status: Any
    tipo: Any
    valor: Any
    comprovante_url: Optional[str] = None
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None
    deleted_at: Optional[datetime] = None
    booking_id: Optional[int] = None
    booking_company_id: Optional[int] = None
    booking_deposit_amount: Optional[Any] = None
    booking_deposit_paid: Optional[bool] = None
    booking_missing: bool = False
    core_status: Optional[Any] = None
    core_amount: Optional[Any] = None
    core_paid_at: Optional[datetime] = None
    core_transaction_id: Optional[str] = None
    core_receipt_url: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class EvidenceAuditResult:
    """
    Resultado da classificação de um registro.

    Args:
        payment_id: ID classificado.
        classification: Classe atribuída.
        reasons: Motivos humanos/legíveis (sem PII).
        before_cutoff: Se ``created_at`` é anterior ao corte técnico do PR #47.
    """

    payment_id: int
    classification: EvidenceClass
    reasons: Sequence[str] = field(default_factory=tuple)
    before_cutoff: Optional[bool] = None


def _norm(value: Any) -> str:
    """
    Normaliza enum/string para comparação case-insensitive.

    Args:
        value: Enum, string ou None.

    Returns:
        Valor em minúsculas, ou string vazia.
    """
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw).strip().lower()


def _as_decimal(value: Any) -> Optional[Decimal]:
    """
    Converte valor monetário para ``Decimal`` quantizado em centavos.

    Args:
        value: Número, string ou Decimal.

    Returns:
        Decimal com 2 casas, ou None se inválido.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _has_text(value: Optional[str]) -> bool:
    """
    Indica se há texto não vazio.

    Args:
        value: String opcional.

    Returns:
        True se há conteúdo após strip.
    """
    return bool(value and str(value).strip())


def _ensure_aware(dt: datetime) -> datetime:
    """
    Garante datetime timezone-aware em UTC para comparação com o corte.

    Args:
        dt: Datetime naive ou aware.

    Returns:
        Datetime em UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def classify_legacy_evidence_payment(
    row: EvidenceAuditInput,
    *,
    cutoff_utc: datetime = PR47_MERGE_UTC,
) -> EvidenceAuditResult:
    """
    Classifica um Payment quanto a evidência legada com cotação em ``valor``.

    A classificação é fail-closed: qualquer ambiguidade vira
    ``REVIEW_REQUIRED``. Nunca promove a PAID nem sugere alterar registros
    com sinais financeiros (``paid_at``, ``transaction_id``, status pago).

    Args:
        row: Snapshot do Payment + booking + CorePayment.
        cutoff_utc: Corte técnico (default = merge do PR #47).

    Returns:
        ``EvidenceAuditResult`` com classe e motivos.
    """
    reasons: List[str] = []
    before_cutoff: Optional[bool] = None
    if row.created_at is not None:
        before_cutoff = _ensure_aware(row.created_at) < _ensure_aware(cutoff_utc)

    status = _norm(row.status)
    tipo = _norm(row.tipo)
    valor = _as_decimal(row.valor)
    deposit = _as_decimal(row.booking_deposit_amount)

    if row.deleted_at is not None:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.EXCLUDE_LEGITIMATE,
            reasons=("soft_deleted",),
            before_cutoff=before_cutoff,
        )

    if tipo in _FINAL or tipo in _REFUND:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.EXCLUDE_LEGITIMATE,
            reasons=("non_deposit_type", f"tipo={tipo or 'empty'}"),
            before_cutoff=before_cutoff,
        )

    if status in _PAID or status in {"refunded", "reembolsado", "failed", "cancelado"}:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.EXCLUDE_LEGITIMATE,
            reasons=("non_pending_status", f"status={status or 'empty'}"),
            before_cutoff=before_cutoff,
        )

    if row.paid_at is not None:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.EXCLUDE_LEGITIMATE,
            reasons=("paid_at_present",),
            before_cutoff=before_cutoff,
        )

    if _has_text(row.transaction_id):
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.EXCLUDE_LEGITIMATE,
            reasons=("transaction_id_present",),
            before_cutoff=before_cutoff,
        )

    if status == "processando":
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("processing_status_ambiguous",),
            before_cutoff=before_cutoff,
        )

    if status not in _PENDING:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("unknown_or_unexpected_status", f"status={status or 'empty'}"),
            before_cutoff=before_cutoff,
        )

    if tipo not in _DEPOSIT:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("unexpected_deposit_type", f"tipo={tipo or 'empty'}"),
            before_cutoff=before_cutoff,
        )

    if not _has_text(row.comprovante_url):
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("missing_comprovante_url",),
            before_cutoff=before_cutoff,
        )

    if row.booking_id is None or row.booking_missing:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("booking_unresolved",),
            before_cutoff=before_cutoff,
        )

    if row.booking_company_id is None:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("tenant_unresolved",),
            before_cutoff=before_cutoff,
        )

    if row.booking_deposit_paid is True:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("deposit_paid_true_with_pending_payment",),
            before_cutoff=before_cutoff,
        )

    core_status = _norm(row.core_status)
    if row.core_status is not None:
        if core_status in _PAID or row.core_paid_at is not None:
            return EvidenceAuditResult(
                payment_id=row.payment_id,
                classification=EvidenceClass.REVIEW_REQUIRED,
                reasons=("core_payment_indicates_paid",),
                before_cutoff=before_cutoff,
            )
        if _has_text(row.core_transaction_id):
            return EvidenceAuditResult(
                payment_id=row.payment_id,
                classification=EvidenceClass.REVIEW_REQUIRED,
                reasons=("core_transaction_id_present",),
                before_cutoff=before_cutoff,
            )
        if core_status and core_status not in _PENDING:
            return EvidenceAuditResult(
                payment_id=row.payment_id,
                classification=EvidenceClass.REVIEW_REQUIRED,
                reasons=("core_status_not_pending", f"core_status={core_status}"),
                before_cutoff=before_cutoff,
            )

    if valor is None:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("invalid_valor",),
            before_cutoff=before_cutoff,
        )

    if valor == EVIDENCE_PLACEHOLDER:
        reasons.append("placeholder_zero")
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.ALREADY_CLEAN,
            reasons=tuple(reasons),
            before_cutoff=before_cutoff,
        )

    if deposit is None or deposit <= EVIDENCE_PLACEHOLDER:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("deposit_amount_missing_or_zero",),
            before_cutoff=before_cutoff,
        )

    if valor != deposit:
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=("valor_differs_from_deposit_amount",),
            before_cutoff=before_cutoff,
        )

    reasons.append("pending_deposit_with_receipt")
    reasons.append("valor_equals_deposit_amount_quote")
    reasons.append("no_financial_transaction_signals")
    if before_cutoff is True:
        reasons.append("created_before_pr47_cutoff")
    elif before_cutoff is False:
        # Pós-corte com cotação ainda em valor: possível outro writer ou
        # deploy atrasado — não assumir backfill automático.
        return EvidenceAuditResult(
            payment_id=row.payment_id,
            classification=EvidenceClass.REVIEW_REQUIRED,
            reasons=(
                "valor_equals_deposit_but_created_after_pr47_cutoff",
                "possible_alternate_writer_or_late_deploy",
            ),
            before_cutoff=before_cutoff,
        )
    else:
        reasons.append("created_at_unknown")

    return EvidenceAuditResult(
        payment_id=row.payment_id,
        classification=EvidenceClass.CANDIDATE_BACKFILL,
        reasons=tuple(reasons),
        before_cutoff=before_cutoff,
    )


def aggregate_audit_results(
    results: Iterable[EvidenceAuditResult],
) -> Dict[str, Any]:
    """
    Agrega contagens de classificação sem expor PII.

    Args:
        results: Iterável de ``EvidenceAuditResult``.

    Returns:
        Dict com totais por classe, IDs candidatos e IDs em revisão.
    """
    counts = {c.value: 0 for c in EvidenceClass}
    candidate_ids: List[int] = []
    review_ids: List[int] = []
    already_clean_ids: List[int] = []
    excluded_ids: List[int] = []
    before_cutoff_candidates = 0

    for item in results:
        counts[item.classification.value] += 1
        if item.classification == EvidenceClass.CANDIDATE_BACKFILL:
            candidate_ids.append(item.payment_id)
            if item.before_cutoff is True:
                before_cutoff_candidates += 1
        elif item.classification == EvidenceClass.REVIEW_REQUIRED:
            review_ids.append(item.payment_id)
        elif item.classification == EvidenceClass.ALREADY_CLEAN:
            already_clean_ids.append(item.payment_id)
        else:
            excluded_ids.append(item.payment_id)

    return {
        "total_classified": sum(counts.values()),
        "counts": counts,
        "candidate_ids": candidate_ids,
        "review_ids": review_ids,
        "already_clean_ids": already_clean_ids,
        "excluded_ids": excluded_ids,
        "candidate_before_cutoff": before_cutoff_candidates,
        "cutoff_utc": PR47_MERGE_UTC.isoformat(),
        "mutation": False,
        "dry_run": True,
    }


def summarize_reason_frequency(
    results: Iterable[EvidenceAuditResult],
) -> Mapping[str, int]:
    """
    Conta frequência de motivos de classificação (agregado).

    Args:
        results: Resultados classificados.

    Returns:
        Mapa motivo → quantidade.
    """
    freq: Dict[str, int] = {}
    for item in results:
        for reason in item.reasons:
            key = reason.split("=")[0]
            freq[key] = freq.get(key, 0) + 1
    return dict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))
