"""
Ensaio local MySQL — validação do seed e classificação dos cenários sintéticos.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from app.modules.payments.legacy_evidence_audit import (
    EVIDENCE_PLACEHOLDER,
    PR47_MERGE_UTC,
    EvidenceAuditInput,
    EvidenceClass,
    classify_legacy_evidence_payment,
)


def _load_seed_module():
    """
    Carrega o script de seed sem executar ``main``.

    Returns:
        Módulo ``seed_legacy_evidence_local``.
    """
    src = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "seed_legacy_evidence_local.py"
    )
    spec = spec_from_file_location("seed_legacy_evidence_local", src)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_assert_local_mysql_url_accepts_localhost():
    """Aceita DSN MySQL local em 127.0.0.1."""
    mod = _load_seed_module()
    url = "mysql+pymysql://coreflow:coreflow@127.0.0.1:3306/coreflow?charset=utf8mb4"
    assert mod.assert_local_mysql_url(url) == url


def test_assert_local_mysql_url_rejects_sqlite():
    """Rejeita SQLite como substituto do ensaio."""
    mod = _load_seed_module()
    with pytest.raises(SystemExit) as exc:
        mod.assert_local_mysql_url("sqlite:///./trancapro.db")
    assert exc.value.code == 2


def test_assert_local_mysql_url_rejects_staging_host():
    """Rejeita host com indicador de staging."""
    mod = _load_seed_module()
    with pytest.raises(SystemExit) as exc:
        mod.assert_local_mysql_url(
            "mysql+pymysql://u:p@db.staging.example:3306/coreflow"
        )
    assert exc.value.code == 2


def test_assert_local_mysql_url_rejects_rds():
    """Rejeita host RDS/AWS."""
    mod = _load_seed_module()
    with pytest.raises(SystemExit) as exc:
        mod.assert_local_mysql_url(
            "mysql+pymysql://u:p@foo.rds.amazonaws.com:3306/coreflow"
        )
    assert exc.value.code == 2


def _case(**kwargs) -> EvidenceAuditInput:
    """
    Snapshot alinhado aos cenários do seed.

    Args:
        **kwargs: Overrides.

    Returns:
        ``EvidenceAuditInput``.
    """
    defaults = dict(
        payment_id=1,
        status="pending",
        tipo="deposit",
        valor=Decimal("90.00"),
        comprovante_url="/static/comprovantes/LOCAL_AUDIT_SEED/x.jpg",
        paid_at=None,
        transaction_id=None,
        booking_id=10,
        booking_company_id=1,
        booking_deposit_amount=Decimal("90.00"),
        booking_deposit_paid=False,
        booking_missing=False,
        core_status="pending",
        core_amount=Decimal("90.00"),
        created_at=PR47_MERGE_UTC - timedelta(days=5),
    )
    defaults.update(kwargs)
    return EvidenceAuditInput(**defaults)


def test_seed_case_a_is_candidate():
    """Caso A (cotação em PENDING) classifica como candidate_backfill."""
    result = classify_legacy_evidence_payment(_case())
    assert result.classification == EvidenceClass.CANDIDATE_BACKFILL


def test_seed_case_b_clean_not_candidate():
    """Caso B (0.00) não é candidato a backfill antigo."""
    result = classify_legacy_evidence_payment(
        _case(valor=EVIDENCE_PLACEHOLDER, core_amount=EVIDENCE_PLACEHOLDER)
    )
    assert result.classification == EvidenceClass.ALREADY_CLEAN


def test_seed_case_c_paid_excluded():
    """Caso C PAID é excluído."""
    result = classify_legacy_evidence_payment(
        _case(
            status="paid",
            paid_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            core_status="paid",
        )
    )
    assert result.classification == EvidenceClass.EXCLUDE_LEGITIMATE


def test_seed_case_d_review_required():
    """Caso D (deposit_paid True + PENDING) exige revisão."""
    result = classify_legacy_evidence_payment(_case(booking_deposit_paid=True))
    assert result.classification == EvidenceClass.REVIEW_REQUIRED


def test_seed_case_e_tenant_b_still_candidate():
    """Caso E (tenant B) permanece candidato — isolamento por company_id no input."""
    result = classify_legacy_evidence_payment(
        _case(payment_id=50, booking_id=50, booking_company_id=2)
    )
    assert result.classification == EvidenceClass.CANDIDATE_BACKFILL
    assert result.payment_id == 50


def test_audit_cli_still_rejects_mutation_flags():
    """Flags de mutação do auditor continuam rejeitadas."""
    src = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "audit_legacy_evidence_pending.py"
    )
    spec = spec_from_file_location("audit_legacy_evidence_pending", src)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit) as exc:
        mod._parse_args(["--apply"])
    assert exc.value.code == 2
