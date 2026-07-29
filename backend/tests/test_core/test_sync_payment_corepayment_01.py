"""
SYNC-PAYMENT-COREPAYMENT-01 — espelhamento explícito Payment → CorePayment.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.paid_amount import get_effective_paid_snapshot
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.payments.legacy_sync import PaymentLegacySyncService
from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType
from app.services.comprovante_service import ComprovanteService
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService
from tests.helpers_ledger import seed_ledger_deposit


class _FakeUpload:
    """
    UploadFile mínimo para testes do comprovante.

    Attributes:
        content_type: MIME type.
        _data: Bytes do arquivo.
    """

    def __init__(self, data: bytes, content_type: str = "image/jpeg"):
        """
        Args:
            data: Conteúdo binário.
            content_type: MIME type simulado.
        """
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        """
        Retorna o conteúdo completo do arquivo fake.

        Returns:
            Bytes do payload.
        """
        return self._data


def _create_booking(db, company, cliente, synced_catalog, **kwargs) -> CoreBooking:
    """
    Persiste um CoreBooking mínimo para testes de sync.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: (catalog, offering).
        **kwargs: Overrides de campos.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    price_total = kwargs.pop("price_total", Decimal("300.00"))
    deposit_amount = kwargs.pop(
        "deposit_amount", (price_total * Decimal("0.30")).quantize(Decimal("0.01"))
    )
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=kwargs.pop(
            "scheduled_at", datetime.now() + timedelta(days=10)
        ),
        status=kwargs.pop("status", ReservationStatus.PENDING_PAYMENT),
        payment_status=kwargs.pop(
            "payment_status", StatusPagamento.PENDING_PAYMENT
        ),
        price_total=price_total,
        deposit_pct=Decimal("0.30"),
        deposit_amount=deposit_amount,
        remaining_amount=(price_total - deposit_amount).quantize(Decimal("0.01")),
        deposit_paid=kwargs.pop("deposit_paid", False),
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=kwargs.pop("created_at", datetime.utcnow()),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_sync_payment_cria_core_payment_idempotente(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Payment novo cria CorePayment; segunda chamada não duplica."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = Payment(
        booking_id=booking.id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("60.00"),
        status=PaymentStatus.PENDING,
    )
    db.add(pag)
    db.flush()

    sync = PaymentLegacySyncService(db)
    core1 = sync.sync_payment(pag, commit=False)
    assert core1 is not None
    assert core1.legacy_payment_id == pag.id
    assert core1.booking_id == booking.id
    assert core1.company_id == default_company.id
    assert core1.amount == Decimal("60.00")
    assert core1.status == CorePaymentStatus.PENDING

    core2 = sync.sync_payment(pag, commit=False)
    db.commit()
    assert core2.id == core1.id
    assert (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .count()
        == 1
    )


def test_sync_payment_atualiza_status_e_valor(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Alteração legítima de Payment atualiza o espelho."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = Payment(
        booking_id=booking.id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("40.00"),
        status=PaymentStatus.PENDING,
    )
    db.add(pag)
    db.flush()
    PaymentLegacySyncService(db).sync_payment(pag, commit=False)

    pag.valor = Decimal("60.00")
    pag.status = PaymentStatus.PAID
    pag.paid_at = datetime.utcnow()
    pag.transaction_id = "tx-sync-01"
    PaymentLegacySyncService(db).sync_payment(pag, commit=True)

    core = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .one()
    )
    assert core.amount == Decimal("60.00")
    assert core.status == CorePaymentStatus.PAID
    assert core.transaction_id == "tx-sync-01"


def test_sync_payment_sem_booking_retorna_none(db):
    """Payment sem booking resolvível não cria CorePayment."""
    pag = Payment(
        booking_id=9_999_999,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("10.00"),
        status=PaymentStatus.PENDING,
    )
    db.add(pag)
    db.flush()
    assert PaymentLegacySyncService(db).sync_payment(pag, commit=False) is None
    assert (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .count()
        == 0
    )


def test_sync_soft_delete_nao_cria_nem_ressuscita(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Soft-delete do Payment espelha deleted_at e não cria órfão novo."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = Payment(
        booking_id=booking.id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("50.00"),
        status=PaymentStatus.PAID,
        paid_at=datetime.utcnow(),
    )
    db.add(pag)
    db.flush()
    PaymentLegacySyncService(db).sync_payment(pag, commit=False)

    pag.deleted_at = datetime.utcnow()
    core = PaymentLegacySyncService(db).sync_payment(pag, commit=True)
    assert core is not None
    assert core.deleted_at is not None

    # Soft-deleted sem espelho prévio: não cria.
    pag2 = Payment(
        booking_id=booking.id,
        tipo=PaymentType.FINAL_PAYMENT,
        valor=Decimal("10.00"),
        status=PaymentStatus.PENDING,
        deleted_at=datetime.utcnow(),
    )
    db.add(pag2)
    db.flush()
    assert PaymentLegacySyncService(db).sync_payment(pag2, commit=True) is None


@pytest.mark.asyncio
async def test_comprovante_espelha_pending_sem_marcar_pago(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Upload de comprovante cria/atualiza Payment PENDING e CorePayment espelho."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(b"\xff\xd8\xff fake-jpeg"),
        base_url="http://testserver",
        company_id=default_company.id,
    )
    assert pag.status == PaymentStatus.PENDING
    assert pag.valor == booking.deposit_amount

    core = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .one()
    )
    assert core.status == CorePaymentStatus.PENDING
    assert core.company_id == default_company.id
    assert core.receipt_url is not None

    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 0
    assert snap.has_processing is False


def test_final_payment_espelha_paid(
    db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Confirmação final espelha Payment FINAL PAID em CorePayment."""
    monkeypatch.setattr(
        "app.modules.booking.application.commands.expire_booking.feature_flags.is_enabled",
        lambda key: key == "booking.core.enabled",
    )
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        status=ReservationStatus.APPROVED,
    )
    seed_ledger_deposit(db, booking, valor=Decimal("60.00"))

    updated = PaymentReservationService(db).confirmar_pagamento_final_por_booking(
        booking.id, default_company.id
    )
    assert updated.payment_status == StatusPagamento.PAID

    pag = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.tipo.in_([PaymentType.FINAL_PAYMENT, PaymentType.FINAL]),
        )
        .one()
    )
    assert pag.status == PaymentStatus.PAID

    core = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .one()
    )
    assert core.status == CorePaymentStatus.PAID
    assert core.payment_type == CorePaymentType.FINAL_PAYMENT
    assert core.company_id == default_company.id


def test_snapshot_apos_sync_payment_paid(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Payment PAID sincronizado alimenta o snapshot sem duplicar valor."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = Payment(
        booking_id=booking.id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("60.00"),
        status=PaymentStatus.PAID,
        paid_at=datetime.utcnow(),
    )
    db.add(pag)
    db.flush()
    PaymentLegacySyncService(db).sync_payment(pag, commit=True)

    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 6_000
    assert snap.payment_cents == 6_000
    assert snap.core_payment_cents == 6_000
    assert snap.is_reconciled is True
    assert snap.has_source_divergence is False


@pytest.fixture
def enable_booking_core(monkeypatch):
    """
    Habilita booking.core.enabled.

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


def test_expiration_tenant_isolation_ainda_passa(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Regressão PR #45: CorePayment alienígena continua ignorado na expiração."""
    from app.models.company import Company, CompanyPlan, CompanySegment

    company_b = Company(
        nome="sync-iso-b",
        slug="sync-iso-b",
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(company_b)
    db.commit()
    db.refresh(company_b)

    booking_a = _create_booking(
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

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    assert booking_a.status == ReservationStatus.EXPIRED
