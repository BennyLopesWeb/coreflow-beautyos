"""
AUDIT-LEGACY-EVIDENCE-PENDING-01 — classificação pura e dry-run read-only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.modules.payments.legacy_evidence_audit import (
    EVIDENCE_PLACEHOLDER,
    PR47_MERGE_UTC,
    EvidenceAuditInput,
    EvidenceClass,
    aggregate_audit_results,
    classify_legacy_evidence_payment,
)


def _base(**kwargs) -> EvidenceAuditInput:
    """
    Monta input típico de comprovante legado com cotação em valor.

    Args:
        **kwargs: Overrides dos campos.

    Returns:
        ``EvidenceAuditInput``.
    """
    defaults = dict(
        payment_id=1,
        status="pending",
        tipo="deposit",
        valor=Decimal("90.00"),
        comprovante_url="/static/comprovantes/x.jpg",
        paid_at=None,
        transaction_id=None,
        deleted_at=None,
        booking_id=10,
        booking_company_id=1,
        booking_deposit_amount=Decimal("90.00"),
        booking_deposit_paid=False,
        booking_missing=False,
        core_status="pending",
        core_amount=Decimal("90.00"),
        core_paid_at=None,
        core_transaction_id=None,
        created_at=PR47_MERGE_UTC - timedelta(days=3),
    )
    defaults.update(kwargs)
    return EvidenceAuditInput(**defaults)


def test_legacy_comprovante_is_candidate():
    """Registro antigo de comprovante com cotação é candidato."""
    result = classify_legacy_evidence_payment(_base())
    assert result.classification == EvidenceClass.CANDIDATE_BACKFILL
    assert result.before_cutoff is True


def test_paid_is_excluded():
    """Payment PAID nunca é candidato."""
    result = classify_legacy_evidence_payment(_base(status="paid", paid_at=datetime.utcnow()))
    assert result.classification == EvidenceClass.EXCLUDE_LEGITIMATE


def test_transaction_id_excluded():
    """Presença de transaction_id exclui."""
    result = classify_legacy_evidence_payment(_base(transaction_id="pix-123"))
    assert result.classification == EvidenceClass.EXCLUDE_LEGITIMATE


def test_paid_at_excluded():
    """paid_at presente exclui mesmo se status pending."""
    result = classify_legacy_evidence_payment(
        _base(paid_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    )
    assert result.classification == EvidenceClass.EXCLUDE_LEGITIMATE


def test_final_payment_excluded():
    """Pagamento final é excluído."""
    result = classify_legacy_evidence_payment(
        _base(tipo="final_payment", comprovante_url=None)
    )
    assert result.classification == EvidenceClass.EXCLUDE_LEGITIMATE


def test_ambiguous_requires_review():
    """Valor diferente da cotação exige revisão."""
    result = classify_legacy_evidence_payment(_base(valor=Decimal("50.00")))
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_missing_tenant_requires_review():
    """Tenant ausente exige revisão."""
    result = classify_legacy_evidence_payment(_base(booking_company_id=None))
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_missing_booking_requires_review():
    """Booking irresolvível exige revisão."""
    result = classify_legacy_evidence_payment(
        _base(booking_missing=True, booking_company_id=None)
    )
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_valor_not_equal_deposit_alone_is_not_candidate():
    """Valor ≠ deposit_amount não vira candidato só por PENDING+URL."""
    result = classify_legacy_evidence_payment(
        _base(valor=Decimal("10.00"), booking_deposit_amount=Decimal("90.00"))
    )
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_new_placeholder_not_mutated():
    """Comprovante novo com 0.00 é ALREADY_CLEAN."""
    result = classify_legacy_evidence_payment(
        _base(valor=EVIDENCE_PLACEHOLDER, core_amount=EVIDENCE_PLACEHOLDER)
    )
    assert result.classification == EvidenceClass.ALREADY_CLEAN


def test_post_cutoff_with_quote_requires_review():
    """Após corte técnico com cotação residual → revisão (não automático)."""
    result = classify_legacy_evidence_payment(
        _base(created_at=PR47_MERGE_UTC + timedelta(hours=2))
    )
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_deposit_paid_true_requires_review():
    """Sinal já confirmado com Payment PENDING é ambíguo."""
    result = classify_legacy_evidence_payment(_base(booking_deposit_paid=True))
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_core_paid_divergence_requires_review():
    """CorePayment PAID com Payment PENDING exige revisão."""
    result = classify_legacy_evidence_payment(
        _base(core_status="paid", core_paid_at=datetime.utcnow())
    )
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_aggregate_idempotent_and_no_paid_leak():
    """Agregação lista só candidatos seguros; PAID não entra."""
    results = [
        classify_legacy_evidence_payment(_base(payment_id=1)),
        classify_legacy_evidence_payment(_base(payment_id=2, status="paid")),
        classify_legacy_evidence_payment(
            _base(payment_id=3, valor=EVIDENCE_PLACEHOLDER)
        ),
        classify_legacy_evidence_payment(_base(payment_id=1)),  # repetição
    ]
    agg = aggregate_audit_results(results)
    assert agg["mutation"] is False
    assert agg["dry_run"] is True
    assert 2 not in agg["candidate_ids"]
    assert agg["counts"][EvidenceClass.CANDIDATE_BACKFILL.value] == 2
    assert agg["counts"][EvidenceClass.EXCLUDE_LEGITIMATE.value] == 1
    assert agg["counts"][EvidenceClass.ALREADY_CLEAN.value] == 1


def test_cli_rejects_mutate_flags():
    """CLI aborta se receber flags de mutação."""
    import importlib.util
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "scripts" / "audit_legacy_evidence_pending.py"
    spec = importlib.util.spec_from_file_location("audit_legacy_evidence_pending", src)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with pytest.raises(SystemExit) as exc:
        mod._parse_args(["--dry-run", "--apply"])
    assert exc.value.code == 2


def test_cli_module_has_no_update_path():
    """Script de auditoria não contém UPDATE SQL embutido."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "scripts" / "audit_legacy_evidence_pending.py"
    text = src.read_text(encoding="utf-8")
    assert "UPDATE " not in text.upper()
    assert "db.commit()" not in text
