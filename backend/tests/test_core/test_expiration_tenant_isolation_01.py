"""
FIX-EXPIRATION-TENANT-ISOLATION-01 — lote de expiração com company_id no snapshot.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType
from app.services.disponibilidade_service import DisponibilidadeService


@pytest.fixture
def enable_booking_core(monkeypatch):
    """
    Habilita ``booking.core.enabled`` para o path de ExpireBookingHandler.

    Args:
        monkeypatch: Fixture pytest.

    Yields:
        None.
    """

    def _flag(key: str) -> bool:
        return key == "booking.core.enabled"

    monkeypatch.setattr(
        "app.modules.booking.application.commands.expire_booking.feature_flags.is_enabled",
        _flag,
    )


def _create_company(db, slug: str) -> Company:
    """
    Persiste empresa auxiliar.

    Args:
        db: Sessão.
        slug: Slug único.

    Returns:
        Company.
    """
    co = Company(
        nome=slug,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


def _create_pending_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    created_at: datetime,
    price_total: Decimal = Decimal("100.00"),
) -> CoreBooking:
    """
    Persiste booking pendente elegível à expiração (sem ledger).

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Par catalog/offering.
        created_at: Timestamp de criação (antigo o suficiente para expirar).
        price_total: Total do serviço.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    deposit_amount = (price_total * Decimal("0.30")).quantize(Decimal("0.01"))
    remaining = (price_total - deposit_amount).quantize(Decimal("0.01"))
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=40),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price_total,
        deposit_pct=Decimal("0.30"),
        deposit_amount=deposit_amount,
        remaining_amount=remaining,
        deposit_paid=False,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=created_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.created_at = created_at
    db.commit()
    db.refresh(row)
    return row


def test_core_payment_outro_tenant_nao_impede_expiracao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """
    CorePayment PAID com company_id alienígena no booking A não protege A.

    Reproduz o risco do lote sem tenant: linha CorePayment aponta para o
    booking da empresa A, mas pertence à empresa B.
    """
    company_b = _create_company(db, "exp-iso-tenant-b")
    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    db.add(
        CorePayment(
            company_id=company_b.id,
            booking_id=booking_a.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("100.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    # Sem filtro de tenant, o snapshot contaria R$100 e bloquearia a expiração.
    snap_global = DisponibilidadeService(db)._load_payment_activation_snapshots(
        [booking_a.id], company_id=None
    )[booking_a.id]
    assert int(snap_global["paid_cents"]) == 10_000

    snap_tenant = DisponibilidadeService(db)._load_payment_activation_snapshots(
        [booking_a.id], company_id=default_company.id
    )[booking_a.id]
    assert int(snap_tenant["paid_cents"]) == 0

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    assert booking_a.status == ReservationStatus.EXPIRED


def test_core_payment_mesmo_tenant_protege_expiracao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """CorePayment PAID do mesmo tenant continua bloqueando a expiração."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    db.add(
        CorePayment(
            company_id=default_company.id,
            booking_id=booking.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("60.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_lote_multi_tenant_isola_snapshots(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """
    No mesmo lote: booking A sem pagamento expira; B com CorePayment próprio não.
    """
    company_b = _create_company(db, "exp-iso-tenant-b2")
    old = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=old,
        price_total=Decimal("300.00"),
    )
    booking_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=old,
        price_total=Decimal("300.00"),
    )
    db.add(
        CorePayment(
            company_id=company_b.id,
            booking_id=booking_b.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("60.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    # CorePayment alienígena no booking A não deve protegê-lo.
    db.add(
        CorePayment(
            company_id=company_b.id,
            booking_id=booking_a.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("100.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.EXPIRED
    assert booking_b.status == ReservationStatus.PENDING_PAYMENT


def test_preload_por_tenant_usa_company_id_do_booking(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Helper de lote agrupa por company_id e zera CorePayment alienígena."""
    company_b = _create_company(db, "exp-iso-tenant-b3")
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
    )
    db.add(
        CorePayment(
            company_id=company_b.id,
            booking_id=booking.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("100.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    snaps = DisponibilidadeService(db)._load_expiration_payment_snapshots_by_tenant(
        [booking]
    )
    assert booking.id in snaps
    assert int(snaps[booking.id]["paid_cents"]) == 0


def test_booking_sem_company_id_fail_closed(db):
    """Sem tenant válido, a avaliação financeira bloqueia expiração."""
    booking = type(
        "B",
        (),
        {
            "id": 999001,
            "company_id": None,
            "price_total": Decimal("100.00"),
            "deposit_paid": False,
            "payment_status": StatusPagamento.PENDING_PAYMENT,
        },
    )()
    assert (
        DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True
    )


def test_payment_mesmo_tenant_ainda_protege(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Payment PAID legítimo do mesmo tenant continua protegendo o booking."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    db.add(
        Payment(
            booking_id=booking.id,
            tipo=PaymentType.DEPOSIT,
            valor=Decimal("60.00"),
            status=PaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
