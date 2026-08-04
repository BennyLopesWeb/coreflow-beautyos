#!/usr/bin/env python3
"""
Seed sintético local — ensaio MySQL Docker da auditoria de evidência.

Uso (somente banco Docker local):

    cd backend
    DATABASE_URL='mysql+pymysql://coreflow:coreflow@127.0.0.1:3306/coreflow?charset=utf8mb4' \\
      python scripts/seed_legacy_evidence_local.py

Limpeza dos dados deste seed (somente marcadores LOCAL_AUDIT_SEED):

    DATABASE_URL='...' python scripts/seed_legacy_evidence_local.py --cleanup

Não usar contra staging/produção. Não imprime DSN nem senhas.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Marcadores sintéticos — idempotência e limpeza segura.
SEED_PREFIX = "LOCAL_AUDIT_SEED"
TENANT_A_SLUG = "local-audit-tenant-a-001"
TENANT_B_SLUG = "local-audit-tenant-b-001"
RECEIPT_A = f"/static/comprovantes/{SEED_PREFIX}/case-a-candidate.jpg"
RECEIPT_B = f"/static/comprovantes/{SEED_PREFIX}/case-b-clean.jpg"
RECEIPT_C = f"/static/comprovantes/{SEED_PREFIX}/case-c-paid.jpg"
RECEIPT_D = f"/static/comprovantes/{SEED_PREFIX}/case-d-review.jpg"
RECEIPT_E = f"/static/comprovantes/{SEED_PREFIX}/case-e-tenant-b.jpg"

_BLOCKED_HOST_FRAGMENTS = (
    "staging",
    "stg.",
    ".stg",
    "prod",
    "production",
    "rds.amazonaws.com",
    "amazonaws.com",
)
_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "mysql"})


def assert_local_mysql_url(url: str) -> str:
    """
    Valida que a URL aponta para MySQL local de ensaio (Docker).

    Args:
        url: ``DATABASE_URL`` candidata.

    Returns:
        A própria URL se válida.

    Raises:
        SystemExit: Se a URL for ausente, SQLite, staging/produção ou host não local.
    """
    if not url or not str(url).strip():
        print("ERRO: DATABASE_URL ausente.", file=sys.stderr)
        raise SystemExit(2)
    raw = str(url).strip()
    lower = raw.lower()
    if lower.startswith("sqlite"):
        print("ERRO: SQLite não é permitido neste ensaio (use MySQL Docker).", file=sys.stderr)
        raise SystemExit(2)
    if not lower.startswith("mysql"):
        print("ERRO: DATABASE_URL deve ser mysql+pymysql para o ensaio local.", file=sys.stderr)
        raise SystemExit(2)
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if not host:
        print("ERRO: host ausente na DATABASE_URL.", file=sys.stderr)
        raise SystemExit(2)
    if any(frag in host for frag in _BLOCKED_HOST_FRAGMENTS):
        print(
            "ERRO: host indica staging/produção/remoto — ensaio abortado.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if host not in _ALLOWED_HOSTS:
        print(
            "ERRO: host não autorizado para ensaio local "
            "(permitido: 127.0.0.1, localhost, mysql).",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return raw


def _session_factory(url: str) -> sessionmaker:
    """
    Cria factory de sessão ligada ao DSN validado.

    Args:
        url: URL MySQL local já validada.

    Returns:
        ``sessionmaker`` configurado.
    """
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ensure_company(db: Session, *, slug: str, nome: str) -> Any:
    """
    Obtém ou cria company sintética pelo slug.

    Args:
        db: Sessão.
        slug: Slug único do tenant de teste.
        nome: Nome comercial sintético.

    Returns:
        Instância ``Company``.
    """
    from app.models.company import Company, CompanyPlan, CompanySegment

    row = db.query(Company).filter(Company.slug == slug).first()
    if row:
        return row
    row = Company(
        nome=nome,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        plugin_id="beauty",
        ativo=True,
    )
    db.add(row)
    db.flush()
    return row


def _ensure_cliente(db: Session, *, company_id: int, telefone: str, nome: str) -> Any:
    """
    Obtém ou cria cliente sintético (telefone único).

    Args:
        db: Sessão.
        company_id: Tenant.
        telefone: Telefone único sintético.
        nome: Nome sintético.

    Returns:
        ``Cliente``.
    """
    from app.models.cliente import Cliente

    row = db.query(Cliente).filter(Cliente.telefone == telefone).first()
    if row:
        return row
    row = Cliente(
        company_id=company_id,
        nome=nome,
        telefone=telefone,
        email=f"{SEED_PREFIX.lower()}.{telefone}@example.test",
    )
    db.add(row)
    db.flush()
    return row


def _ensure_catalog_offering(
    db: Session, *, company_id: int, slug: str
) -> Tuple[Any, Any]:
    """
    Obtém ou cria catalog/offering sintéticos para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        slug: Slug do catálogo (único por company).

    Returns:
        Tupla ``(CoreCatalog, CoreOffering)``.
    """
    from app.modules.catalog.domain.models import CoreCatalog, CoreOffering

    catalog = (
        db.query(CoreCatalog)
        .filter(CoreCatalog.company_id == company_id, CoreCatalog.slug == slug)
        .first()
    )
    if not catalog:
        catalog = CoreCatalog(
            company_id=company_id,
            name=f"{SEED_PREFIX} Catalog",
            slug=slug,
            description="Synthetic catalog for local audit rehearsal",
            images=[],
            active=True,
            plugin_metadata={"seed": SEED_PREFIX},
        )
        db.add(catalog)
        db.flush()

    offering = (
        db.query(CoreOffering)
        .filter(
            CoreOffering.company_id == company_id,
            CoreOffering.catalog_id == catalog.id,
            CoreOffering.name == f"{SEED_PREFIX} Offering",
        )
        .first()
    )
    if not offering:
        offering = CoreOffering(
            company_id=company_id,
            catalog_id=catalog.id,
            name=f"{SEED_PREFIX} Offering",
            description="Synthetic offering",
            price_total=Decimal("300.00"),
            deposit_pct=Decimal("0.30"),
            deposit_amount=Decimal("90.00"),
            duration_minutes=120,
            active=True,
            plugin_metadata={"seed": SEED_PREFIX},
        )
        db.add(offering)
        db.flush()
    return catalog, offering


def _ensure_booking(
    db: Session,
    *,
    company_id: int,
    customer_id: int,
    catalog_id: int,
    offering_id: int,
    notes: str,
    deposit_amount: Decimal,
    deposit_paid: bool = False,
) -> Any:
    """
    Obtém ou cria booking sintético identificado por ``notes``.

    Args:
        db: Sessão.
        company_id: Tenant.
        customer_id: Cliente.
        catalog_id: Catálogo.
        offering_id: Offering.
        notes: Marcador único do cenário.
        deposit_amount: Cotação.
        deposit_paid: Flag administrativa.

    Returns:
        ``CoreBooking``.
    """
    from app.models.agendamento import ReservationStatus, StatusPagamento
    from app.modules.booking.domain.models import CoreBooking

    row = (
        db.query(CoreBooking)
        .filter(
            CoreBooking.company_id == company_id,
            CoreBooking.notes == notes,
            CoreBooking.deleted_at.is_(None),
        )
        .first()
    )
    if row:
        return row
    price = Decimal("300.00")
    row = CoreBooking(
        company_id=company_id,
        customer_id=customer_id,
        catalog_id=catalog_id,
        offering_id=offering_id,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price,
        deposit_pct=Decimal("0.30"),
        deposit_amount=deposit_amount,
        remaining_amount=(price - deposit_amount).quantize(Decimal("0.01")),
        deposit_paid=deposit_paid,
        notes=notes,
        sync_status="synced",
        version=1,
    )
    db.add(row)
    db.flush()
    return row


def _ensure_payment_pair(
    db: Session,
    *,
    company_id: int,
    booking_id: int,
    receipt_url: str,
    valor: Decimal,
    status: Any,
    paid_at: Optional[datetime],
    created_at: Optional[datetime],
    core_status: Any,
    core_amount: Decimal,
    core_paid_at: Optional[datetime] = None,
) -> Tuple[Any, Any]:
    """
    Obtém ou cria Payment + CorePayment sintéticos pela ``comprovante_url``.

    Args:
        db: Sessão.
        company_id: Tenant.
        booking_id: Booking.
        receipt_url: URL marcadora (idempotência).
        valor: ``Payment.valor``.
        status: Status do Payment.
        paid_at: Timestamp de liquidação.
        created_at: Criação (corte PR #47).
        core_status: Status do espelho.
        core_amount: Amount do espelho.
        core_paid_at: paid_at do espelho.

    Returns:
        Tupla ``(Payment, CorePayment)``.
    """
    from app.models.payment import Payment, PaymentType
    from app.modules.payments.models import CorePayment, CorePaymentType

    pag = (
        db.query(Payment)
        .filter(Payment.comprovante_url == receipt_url, Payment.deleted_at.is_(None))
        .first()
    )
    if not pag:
        pag = Payment(
            booking_id=booking_id,
            tipo=PaymentType.DEPOSIT,
            valor=valor,
            status=status,
            comprovante_url=receipt_url,
            paid_at=paid_at,
            transaction_id=None,
        )
        db.add(pag)
        db.flush()
    else:
        pag.valor = valor
        pag.status = status
        pag.paid_at = paid_at
        pag.booking_id = booking_id

    if created_at is not None:
        pag.created_at = created_at

    core = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id, CorePayment.deleted_at.is_(None))
        .first()
    )
    if not core:
        core = CorePayment(
            company_id=company_id,
            booking_id=booking_id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=core_amount,
            status=core_status,
            receipt_url=receipt_url,
            paid_at=core_paid_at,
            legacy_payment_id=pag.id,
        )
        db.add(core)
        db.flush()
    else:
        core.amount = core_amount
        core.status = core_status
        core.paid_at = core_paid_at
        core.receipt_url = receipt_url
        core.company_id = company_id
        core.booking_id = booking_id
    return pag, core


def seed(db: Session) -> Dict[str, Any]:
    """
    Insere/atualiza cenários sintéticos A–E de forma idempotente.

    Args:
        db: Sessão MySQL local.

    Returns:
        Contagens por cenário (sem PII).
    """
    from app.models.payment import PaymentStatus
    from app.modules.payments.legacy_evidence_audit import PR47_MERGE_UTC
    from app.modules.payments.models import CorePaymentStatus

    company_a = _ensure_company(
        db, slug=TENANT_A_SLUG, nome="LOCAL AUDIT Tenant A (synthetic)"
    )
    company_b = _ensure_company(
        db, slug=TENANT_B_SLUG, nome="LOCAL AUDIT Tenant B (synthetic)"
    )
    cliente_a = _ensure_cliente(
        db,
        company_id=company_a.id,
        telefone="11990000001",
        nome="LOCAL AUDIT Client A",
    )
    cliente_b = _ensure_cliente(
        db,
        company_id=company_b.id,
        telefone="11990000002",
        nome="LOCAL AUDIT Client B",
    )
    catalog_a, offering_a = _ensure_catalog_offering(
        db, company_id=company_a.id, slug=f"{SEED_PREFIX.lower()}-cat-a"
    )
    catalog_b, offering_b = _ensure_catalog_offering(
        db, company_id=company_b.id, slug=f"{SEED_PREFIX.lower()}-cat-b"
    )

    deposit = Decimal("90.00")
    before_cutoff = PR47_MERGE_UTC - timedelta(days=5)

    # Caso A — candidato a backfill
    booking_a = _ensure_booking(
        db,
        company_id=company_a.id,
        customer_id=cliente_a.id,
        catalog_id=catalog_a.id,
        offering_id=offering_a.id,
        notes=f"{SEED_PREFIX}:case-a-candidate",
        deposit_amount=deposit,
    )
    _ensure_payment_pair(
        db,
        company_id=company_a.id,
        booking_id=booking_a.id,
        receipt_url=RECEIPT_A,
        valor=deposit,
        status=PaymentStatus.PENDING,
        paid_at=None,
        created_at=before_cutoff,
        core_status=CorePaymentStatus.PENDING,
        core_amount=deposit,
    )

    # Caso B — evidência nova correta (0.00)
    booking_b = _ensure_booking(
        db,
        company_id=company_a.id,
        customer_id=cliente_a.id,
        catalog_id=catalog_a.id,
        offering_id=offering_a.id,
        notes=f"{SEED_PREFIX}:case-b-clean",
        deposit_amount=deposit,
    )
    _ensure_payment_pair(
        db,
        company_id=company_a.id,
        booking_id=booking_b.id,
        receipt_url=RECEIPT_B,
        valor=Decimal("0.00"),
        status=PaymentStatus.PENDING,
        paid_at=None,
        created_at=PR47_MERGE_UTC + timedelta(days=1),
        core_status=CorePaymentStatus.PENDING,
        core_amount=Decimal("0.00"),
    )

    # Caso C — pagamento liquidado
    booking_c = _ensure_booking(
        db,
        company_id=company_a.id,
        customer_id=cliente_a.id,
        catalog_id=catalog_a.id,
        offering_id=offering_a.id,
        notes=f"{SEED_PREFIX}:case-c-paid",
        deposit_amount=deposit,
        deposit_paid=True,
    )
    paid_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    _ensure_payment_pair(
        db,
        company_id=company_a.id,
        booking_id=booking_c.id,
        receipt_url=RECEIPT_C,
        valor=deposit,
        status=PaymentStatus.PAID,
        paid_at=paid_at,
        created_at=before_cutoff,
        core_status=CorePaymentStatus.PAID,
        core_amount=deposit,
        core_paid_at=paid_at,
    )

    # Caso D — REVIEW: PENDING com cotação + deposit_paid True
    booking_d = _ensure_booking(
        db,
        company_id=company_a.id,
        customer_id=cliente_a.id,
        catalog_id=catalog_a.id,
        offering_id=offering_a.id,
        notes=f"{SEED_PREFIX}:case-d-review",
        deposit_amount=deposit,
        deposit_paid=True,
    )
    _ensure_payment_pair(
        db,
        company_id=company_a.id,
        booking_id=booking_d.id,
        receipt_url=RECEIPT_D,
        valor=deposit,
        status=PaymentStatus.PENDING,
        paid_at=None,
        created_at=before_cutoff,
        core_status=CorePaymentStatus.PENDING,
        core_amount=deposit,
    )

    # Caso E — tenant B candidato (isolamento)
    booking_e = _ensure_booking(
        db,
        company_id=company_b.id,
        customer_id=cliente_b.id,
        catalog_id=catalog_b.id,
        offering_id=offering_b.id,
        notes=f"{SEED_PREFIX}:case-e-tenant-b",
        deposit_amount=deposit,
    )
    _ensure_payment_pair(
        db,
        company_id=company_b.id,
        booking_id=booking_e.id,
        receipt_url=RECEIPT_E,
        valor=deposit,
        status=PaymentStatus.PENDING,
        paid_at=None,
        created_at=before_cutoff,
        core_status=CorePaymentStatus.PENDING,
        core_amount=deposit,
    )

    db.commit()
    return {
        "seed_prefix": SEED_PREFIX,
        "tenants": [TENANT_A_SLUG, TENANT_B_SLUG],
        "scenarios": {
            "case_a_candidate": RECEIPT_A,
            "case_b_clean": RECEIPT_B,
            "case_c_paid": RECEIPT_C,
            "case_d_review": RECEIPT_D,
            "case_e_tenant_b": RECEIPT_E,
        },
        "mutation_outside_seed_markers": False,
    }


def cleanup(db: Session) -> Dict[str, int]:
    """
    Remove somente registros marcados com ``LOCAL_AUDIT_SEED``.

    Args:
        db: Sessão MySQL local.

    Returns:
        Contagens removidas por entidade.
    """
    from app.models.cliente import Cliente
    from app.models.company import Company
    from app.models.payment import Payment
    from app.modules.booking.domain.models import CoreBooking
    from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
    from app.modules.payments.models import CorePayment

    counts = {"core_payments": 0, "payments": 0, "bookings": 0, "offerings": 0, "catalogs": 0, "clientes": 0, "companies": 0}

    payments = (
        db.query(Payment)
        .filter(Payment.comprovante_url.like(f"%{SEED_PREFIX}%"))
        .all()
    )
    payment_ids = [p.id for p in payments]
    if payment_ids:
        cores = (
            db.query(CorePayment)
            .filter(CorePayment.legacy_payment_id.in_(payment_ids))
            .all()
        )
        for c in cores:
            db.delete(c)
            counts["core_payments"] += 1
        for p in payments:
            db.delete(p)
            counts["payments"] += 1

    bookings = (
        db.query(CoreBooking)
        .filter(CoreBooking.notes.like(f"{SEED_PREFIX}%"))
        .all()
    )
    for b in bookings:
        db.delete(b)
        counts["bookings"] += 1

    companies = (
        db.query(Company)
        .filter(Company.slug.in_([TENANT_A_SLUG, TENANT_B_SLUG]))
        .all()
    )
    company_ids = [c.id for c in companies]
    if company_ids:
        for o in (
            db.query(CoreOffering)
            .filter(CoreOffering.company_id.in_(company_ids))
            .all()
        ):
            db.delete(o)
            counts["offerings"] += 1
        for cat in (
            db.query(CoreCatalog)
            .filter(CoreCatalog.company_id.in_(company_ids))
            .all()
        ):
            db.delete(cat)
            counts["catalogs"] += 1
        for cli in (
            db.query(Cliente)
            .filter(Cliente.company_id.in_(company_ids))
            .all()
        ):
            db.delete(cli)
            counts["clientes"] += 1
        for c in companies:
            db.delete(c)
            counts["companies"] += 1

    db.commit()
    return counts


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entry-point CLI do seed local.

    Args:
        argv: Argumentos opcionais.

    Returns:
        Código de saída (0 sucesso, 2 URL inválida).
    """
    parser = argparse.ArgumentParser(
        description="Seed sintético LOCAL_AUDIT_SEED para ensaio MySQL Docker."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove somente dados marcados LOCAL_AUDIT_SEED.",
    )
    args = parser.parse_args(argv)

    url = assert_local_mysql_url(os.environ.get("DATABASE_URL", ""))
    SessionLocal = _session_factory(url)
    db = SessionLocal()
    try:
        if args.cleanup:
            removed = cleanup(db)
            print("CLEANUP LOCAL_AUDIT_SEED (synthetic only)")
            print(removed)
            return 0
        report = seed(db)
        print("SEED LOCAL_AUDIT_SEED OK (synthetic, local MySQL only)")
        print(report)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
