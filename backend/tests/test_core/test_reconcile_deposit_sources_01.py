"""
RECONCILE-DEPOSIT-SOURCES-01 — revisão: snapshot, divergência, fail-closed.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import MinimumDepositNotMetError, ValidationError
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.activation import calculate_minimum_activation_cents
from app.modules.booking.domain.policy.paid_amount import (
    get_effective_paid_snapshot,
    load_effective_paid_snapshots,
)
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService


def _create_booking(db, company, cliente, synced_catalog, *, price_total, deposit_amount):
    """
    Cria booking pendente.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Fixture.
        price_total: Total.
        deposit_amount: Cotação comercial (não é pagamento).

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=5),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price_total,
        deposit_amount=deposit_amount,
        remaining_amount=(price_total - deposit_amount).quantize(Decimal("0.01")),
        deposit_paid=False,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _pay(db, booking_id, valor, *, status=PaymentStatus.PAID, tipo=PaymentType.DEPOSIT, deleted=False):
    """Insere Payment no ledger."""
    pag = Payment(
        booking_id=booking_id,
        tipo=tipo,
        valor=valor,
        status=status,
        paid_at=datetime.utcnow() if status in (PaymentStatus.PAID, PaymentStatus.PAGO) else None,
        deleted_at=datetime.utcnow() if deleted else None,
    )
    db.add(pag)
    db.commit()
    db.refresh(pag)
    return pag


def _core_pay(db, company_id, booking_id, amount, *, status=CorePaymentStatus.PAID):
    """Insere CorePayment no ledger."""
    row = CorePayment(
        company_id=company_id,
        booking_id=booking_id,
        payment_type=CorePaymentType.DEPOSIT,
        amount=amount,
        status=status,
        paid_at=datetime.utcnow() if status == CorePaymentStatus.PAID else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_fontes_mesmo_valor(db, default_company, cliente_exemplo, synced_catalog):
    """Payment e CorePayment iguais → reconciliado, source both."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    _core_pay(db, default_company.id, booking.id, Decimal("60.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 6_000
    assert snap.payment_cents == 6_000
    assert snap.core_payment_cents == 6_000
    assert snap.source_used == "both"
    assert snap.has_source_divergence is False
    assert snap.is_reconciled is True
    assert snap.currency == "BRL"


def test_fontes_divergentes_bloqueiam_ativacao_e_expiracao(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Divergência material: não ativa e não libera expiração."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    _core_pay(db, default_company.id, booking.id, Decimal("50.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.has_source_divergence is True
    assert snap.is_reconciled is False
    assert snap.payment_cents == 6_000
    assert snap.core_payment_cents == 5_000

    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    db.refresh(booking)
    assert booking.deposit_paid is False

    # Fail-closed: não expira automaticamente
    assert DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True


def test_uma_fonte_vazia(db, default_company, cliente_exemplo, synced_catalog):
    """Apenas Payment → source payment, reconciliado."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.source_used == "payment"
    assert snap.core_payment_cents == 0
    assert snap.is_reconciled is True
    assert snap.has_source_divergence is False


def test_processing_bloqueia_ativacao_e_expiracao(
    db, default_company, cliente_exemplo, synced_catalog
):
    """processando não conta e bloqueia decisão automática."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"), status=PaymentStatus.PROCESSANDO)
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 0
    assert snap.has_processing is True

    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    assert DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True


def test_falha_consulta_fail_closed_ativacao_e_expiracao(
    db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Erro em consulta financeira → fail-closed nos dois fluxos."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )

    def _boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(
        "app.services.payment_reservation_service.get_effective_paid_snapshot",
        _boom,
    )
    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )

    svc = DisponibilidadeService(db)
    svc._load_payment_activation_snapshots = _boom  # type: ignore[method-assign]
    assert svc._has_minimum_activation_payment(booking) is True


def test_duplicidade_max_sinalizada_quando_igual(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Mesmo valor nas duas fontes não duplica e fica reconciliado."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    _core_pay(db, default_company.id, booking.id, Decimal("60.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 6_000
    assert snap.is_reconciled is True


def test_retry_confirm_idempotent(db, default_company, cliente_exemplo, synced_catalog):
    """Retry após ativação não altera estado."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    svc = PaymentReservationService(db)
    a = svc.confirmar_deposito_por_booking(booking.id, default_company.id)
    b = svc.confirmar_deposito_por_booking(booking.id, default_company.id)
    assert a.deposit_paid and b.deposit_paid


def test_dois_pagamentos_parciais(db, default_company, cliente_exemplo, synced_catalog):
    """Parcelas somam na mesma fonte."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("30.00"),
    )
    _pay(db, booking.id, Decimal("30.00"))
    _pay(db, booking.id, Decimal("30.00"), tipo=PaymentType.FINAL_PAYMENT)
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 6_000


def test_outro_tenant(db, default_company, cliente_exemplo, synced_catalog):
    """CorePayment de outro tenant não conta."""
    other = Company(
        nome="Other",
        slug="reconcile-rev-other",
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _core_pay(db, other.id, booking.id, Decimal("60.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 0
    assert snap.source_used == "none"


def test_snapshot_comercial_divergente_nao_ativa(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Cotação alta sem ledger → não ativa."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    with pytest.raises(MinimumDepositNotMetError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )


def test_ativacao_e_expirador_mesma_decisao(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Mesmo paid_cents e mesma decisão de proteção."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("800.00"), deposit_amount=Decimal("100.00"),
    )
    _pay(db, booking.id, Decimal("100.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    exp = DisponibilidadeService(db)._load_payment_activation_snapshots(
        [booking.id], company_id=default_company.id
    )[booking.id]
    assert snap.paid_cents == exp["paid_cents"] == 10_000
    assert snap.is_reconciled is exp["is_reconciled"] is True
    assert snap.paid_cents >= calculate_minimum_activation_cents(80_000)
    updated = PaymentReservationService(db).confirmar_deposito_por_booking(
        booking.id, default_company.id
    )
    assert updated.deposit_paid is True
    # Após ativo, expirador continua protegendo
    db.refresh(booking)
    assert DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True


def test_abaixo_minimo_preserva_para_analise(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Ledger abaixo do mínimo: Payment permanece, booking não ativa."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("59.99"))
    with pytest.raises(MinimumDepositNotMetError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    db.refresh(booking)
    assert booking.deposit_paid is False
    assert (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.deleted_at.is_(None))
        .count()
        == 1
    )


def test_contrato_snapshot_campos(db, default_company, cliente_exemplo, synced_catalog):
    """Snapshot expõe todos os campos de reconciliação."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    snap = load_effective_paid_snapshots(
        db, [booking.id], company_id=default_company.id
    )[booking.id]
    for field in (
        "paid_cents",
        "payment_cents",
        "core_payment_cents",
        "source_used",
        "has_processing",
        "has_paid_rows",
        "has_source_divergence",
        "is_reconciled",
        "currency",
    ):
        assert hasattr(snap, field)


def test_moeda_padrao_brl(db, default_company, cliente_exemplo, synced_catalog):
    """Domínio atual não persiste moeda por pagamento — snapshot sempre BRL."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )
    _pay(db, booking.id, Decimal("60.00"))
    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.currency == "BRL"


def test_falha_uma_fonte_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Falha ao consultar Payment (query) → fail-closed na ativação."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )

    def _boom_query(self, *args, **kwargs):
        raise RuntimeError("payment source down")

    monkeypatch.setattr(
        "sqlalchemy.orm.Query.all",
        _boom_query,
    )
    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )


def test_falha_duas_fontes_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Falha geral do loader → fail-closed na ativação e no expirador."""
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"), deposit_amount=Decimal("90.00"),
    )

    def _boom(*_a, **_k):
        raise RuntimeError("both sources down")

    monkeypatch.setattr(
        "app.services.disponibilidade_service.load_effective_paid_snapshots",
        _boom,
    )
    monkeypatch.setattr(
        "app.services.payment_reservation_service.get_effective_paid_snapshot",
        _boom,
    )
    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    assert DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True
