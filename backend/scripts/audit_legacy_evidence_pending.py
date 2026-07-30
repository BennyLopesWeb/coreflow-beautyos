#!/usr/bin/env python3
"""
AUDIT-LEGACY-EVIDENCE-PENDING-01 — auditoria read-only / dry-run.

Uso:
    cd backend
    python scripts/audit_legacy_evidence_pending.py --dry-run
    python scripts/audit_legacy_evidence_pending.py --dry-run --json-out /tmp/legacy-evidence-audit.json

Segurança:
    - não executa UPDATE/DELETE;
    - não aceita flags de mutação;
    - relatório contém apenas IDs e contagens (sem URLs/PII).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.payment import Payment, PaymentType
from app.modules.booking.domain.models import CoreBooking
# Relacionamentos ORM exigidos pelo mapper de CoreBooking.
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering  # noqa: F401
from app.modules.payments.legacy_evidence_audit import (
    EvidenceAuditInput,
    EvidenceAuditResult,
    aggregate_audit_results,
    classify_legacy_evidence_payment,
    summarize_reason_frequency,
)
from app.modules.payments.models import CorePayment


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parseia argumentos da CLI.

    Args:
        argv: Lista de argumentos (default: ``sys.argv[1:]``).

    Returns:
        Namespace validado.

    Raises:
        SystemExit: Se flags de mutação forem passadas.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Audita Payments PENDING de comprovante com possível cotação em valor "
            "(somente leitura)."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Obrigatório semanticamente: nunca muta (default True).",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="Caminho opcional para gravar JSON agregado (fora do git).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limite opcional de linhas Payment a classificar (0 = todas).",
    )
    # Flags proibidas — se presentes, aborta.
    known_bad = {
        "--apply",
        "--execute",
        "--mutate",
        "--write",
        "--update",
        "--backfill",
        "--commit",
    }
    raw = list(argv if argv is not None else sys.argv[1:])
    for token in raw:
        name = token.split("=")[0]
        if name in known_bad:
            print(
                f"ERRO: flag proibida nesta auditoria: {name}. "
                "Somente --dry-run é permitido.",
                file=sys.stderr,
            )
            raise SystemExit(2)
    return parser.parse_args(raw)


def _load_rows(db: Session, limit: int) -> List[EvidenceAuditInput]:
    """
    Carrega Payments DEPOSIT/SINAL (não deletados) e contexto de booking/core.

    Args:
        db: Sessão SQLAlchemy (somente leitura).
        limit: Máximo de linhas (0 = sem limite).

    Returns:
        Lista de ``EvidenceAuditInput``.
    """
    q = (
        db.query(Payment)
        .filter(
            Payment.deleted_at.is_(None),
            Payment.tipo.in_([PaymentType.DEPOSIT, PaymentType.SINAL]),
        )
        .order_by(Payment.id.asc())
    )
    if limit > 0:
        q = q.limit(limit)
    payments = q.all()
    if not payments:
        return []

    booking_ids = {p.booking_id for p in payments if p.booking_id is not None}
    bookings: Dict[int, CoreBooking] = {}
    if booking_ids:
        for b in (
            db.query(CoreBooking)
            .filter(CoreBooking.id.in_(list(booking_ids)))
            .all()
        ):
            bookings[int(b.id)] = b

    payment_ids = [int(p.id) for p in payments]
    cores: Dict[int, CorePayment] = {}
    if payment_ids:
        for c in (
            db.query(CorePayment)
            .filter(
                CorePayment.legacy_payment_id.in_(payment_ids),
                CorePayment.deleted_at.is_(None),
            )
            .all()
        ):
            if c.legacy_payment_id is not None:
                cores[int(c.legacy_payment_id)] = c

    rows: List[EvidenceAuditInput] = []
    for p in payments:
        booking = bookings.get(int(p.booking_id)) if p.booking_id is not None else None
        core = cores.get(int(p.id))
        rows.append(
            EvidenceAuditInput(
                payment_id=int(p.id),
                status=p.status,
                tipo=p.tipo,
                valor=p.valor,
                comprovante_url=p.comprovante_url,
                paid_at=p.paid_at,
                transaction_id=p.transaction_id,
                deleted_at=p.deleted_at,
                booking_id=int(p.booking_id) if p.booking_id is not None else None,
                booking_company_id=(
                    int(booking.company_id) if booking is not None else None
                ),
                booking_deposit_amount=(
                    booking.deposit_amount if booking is not None else None
                ),
                booking_deposit_paid=(
                    bool(booking.deposit_paid) if booking is not None else None
                ),
                booking_missing=(p.booking_id is not None and booking is None),
                core_status=core.status if core is not None else None,
                core_amount=core.amount if core is not None else None,
                core_paid_at=core.paid_at if core is not None else None,
                core_transaction_id=(
                    core.transaction_id if core is not None else None
                ),
                core_receipt_url=core.receipt_url if core is not None else None,
                created_at=p.created_at,
            )
        )
    return rows


def _extra_aggregates(db: Session, rows: List[EvidenceAuditInput]) -> Dict[str, Any]:
    """
    Calcula agregados auxiliares do universo DEPOSIT/SINAL carregado.

    Args:
        db: Sessão (não usada para mutação; mantida por simetria futura).
        rows: Inputs carregados.

    Returns:
        Dict de contagens auxiliares.
    """
    del db  # read-path explícito; sem queries extras mutáveis.
    with_receipt = 0
    without_receipt = 0
    valor_zero = 0
    valor_eq_deposit = 0
    with_paid_at = 0
    with_tx = 0
    pending = 0
    by_tenant: Counter = Counter()

    for row in rows:
        if row.comprovante_url and str(row.comprovante_url).strip():
            with_receipt += 1
        else:
            without_receipt += 1
        try:
            valor = Decimal(str(row.valor)).quantize(Decimal("0.01"))
        except Exception:
            valor = None
        if valor == Decimal("0.00"):
            valor_zero += 1
        deposit = None
        if row.booking_deposit_amount is not None:
            try:
                deposit = Decimal(str(row.booking_deposit_amount)).quantize(
                    Decimal("0.01")
                )
            except Exception:
                deposit = None
        if valor is not None and deposit is not None and valor == deposit:
            valor_eq_deposit += 1
        if row.paid_at is not None:
            with_paid_at += 1
        if row.transaction_id and str(row.transaction_id).strip():
            with_tx += 1
        status = str(getattr(row.status, "value", row.status) or "").lower()
        if status in {"pending", "pendente"}:
            pending += 1
        if row.booking_company_id is not None:
            by_tenant[str(row.booking_company_id)] += 1

    return {
        "deposit_sinal_loaded": len(rows),
        "with_comprovante_url": with_receipt,
        "without_comprovante_url": without_receipt,
        "valor_zero": valor_zero,
        "valor_equals_deposit_amount": valor_eq_deposit,
        "with_paid_at": with_paid_at,
        "with_transaction_id": with_tx,
        "pending_status": pending,
        "by_tenant_counts": dict(by_tenant),
    }


def run_dry_run(*, limit: int = 0, json_out: str = "") -> Dict[str, Any]:
    """
    Executa a auditoria em modo dry-run (sem UPDATE).

    Args:
        limit: Limite opcional de linhas.
        json_out: Caminho opcional para JSON.

    Returns:
        Relatório agregado.
    """
    db = SessionLocal()
    try:
        inputs = _load_rows(db, limit=limit)
        results: List[EvidenceAuditResult] = [
            classify_legacy_evidence_payment(row) for row in inputs
        ]
        report = aggregate_audit_results(results)
        report["universe"] = _extra_aggregates(db, inputs)
        report["reason_frequency"] = dict(summarize_reason_frequency(results))
        report["generated_at"] = datetime.utcnow().isoformat() + "Z"
        report["note"] = (
            "Ambiente local/configurado via DATABASE_URL; "
            "números não representam produção a menos que o DSN aponte para ela."
        )
    finally:
        db.close()

    if json_out:
        out_path = Path(json_out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        report["json_out"] = str(out_path)

    return report


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entry-point CLI.

    Args:
        argv: Argumentos opcionais.

    Returns:
        Código de saída (0 sucesso, 2 flag proibida).
    """
    args = _parse_args(argv)
    if not args.dry_run:
        print("ERRO: auditoria exige --dry-run.", file=sys.stderr)
        return 2

    report = run_dry_run(limit=args.limit, json_out=args.json_out)
    print("AUDIT-LEGACY-EVIDENCE-PENDING-01 (dry-run, mutation=false)")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    # Garantia explícita de não mutação.
    assert report.get("mutation") is False
    assert report.get("dry_run") is True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
