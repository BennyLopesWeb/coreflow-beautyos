"""
RECONCILE-DEPOSIT-SOURCES-01 — fonte canônica do valor pago (ativação = expirador).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import MinimumDepositNotMetError
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    money_to_cents,
)
from app.modules.booking.domain.policy.paid_amount import (
    get_effective_paid_amount_cents,
    load_effective_paid_snapshots,
)
from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService


def _create_booking(
    db,
    company,
    cliente,
    synced_catalog,
    *,
    price_total: Decimal,
    deposit_amount: Decimal,
):
    """
    Cria ``CoreBooking`` pendente para testes de reconciliação.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Fixture (catalog, offering).
        price_total: Total do serviço.
        deposit_amount: Snapshot comercial do sinal.

    Returns:
        CoreBooking persistido.
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


def _add_payment(
    db,
    booking_id: int,
    *,
    valor: Decimal,
    status=PaymentStatus.PAID,
    tipo=PaymentType.DEPOSIT,
    deleted: bool = False,
):
    """
    Insere linha ``Payment`` ligada ao booking.

    Args:
        db: Sessão.
        booking_id: ID do booking.
        valor: Valor em reais.
        status: Status do pagamento.
        tipo: Tipo do pagamento.
        deleted: Se True, marca soft-delete.

    Returns:
        Payment persistido.
    """
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


def _add_core_payment(
    db,
    company_id: int,
    booking_id: int,
    *,
    amount: Decimal,
    status=CorePaymentStatus.PAID,
):
    """
    Insere ``CorePayment`` no tenant/booking.

    Args:
        db: Sessão.
        company_id: Tenant.
        booking_id: Booking.
        amount: Valor.
        status: Status.

    Returns:
        CorePayment persistido.
    """
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


def test_01_sem_pagamento_zero(db, default_company, cliente_exemplo, synced_catalog):
    """Sem pagamento → valor efetivo zero."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 0
    )


@pytest.mark.parametrize(
    "valor,expected_active",
    [
        (Decimal("60.00"), True),
        (Decimal("60.01"), True),
        (Decimal("59.99"), False),
    ],
)
def test_02_03_04_pagamento_valido_em_relacao_ao_minimo(
    db, default_company, cliente_exemplo, synced_catalog, valor, expected_active
):
    """Pagamento válido no/acima/abaixo do mínimo."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=valor,
    )
    _add_payment(db, booking.id, valor=valor)
    paid = get_effective_paid_amount_cents(
        db, booking_id=booking.id, company_id=default_company.id
    )
    minimum = calculate_minimum_activation_cents(30_000)
    assert (paid >= minimum) is expected_active


@pytest.mark.parametrize(
    "status",
    [
        PaymentStatus.PENDING,
        PaymentStatus.FAILED,
        PaymentStatus.REFUNDED,
        PaymentStatus.CANCELADO,
    ],
)
def test_05_08_status_invalidos_nao_contam(
    db, default_company, cliente_exemplo, synced_catalog, status
):
    """Pending/failed/refunded/cancelado não contam."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_payment(db, booking.id, valor=Decimal("60.00"), status=status)
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 0
    )


def test_09_soft_deleted_nao_conta(db, default_company, cliente_exemplo, synced_catalog):
    """Pagamento soft-deleted não conta."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_payment(db, booking.id, valor=Decimal("60.00"), deleted=True)
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 0
    )


def test_10_outro_booking_nao_conta(db, default_company, cliente_exemplo, synced_catalog):
    """Pagamento de outro booking não conta."""
    a = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    b = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_payment(db, b.id, valor=Decimal("60.00"))
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=a.id, company_id=default_company.id
        )
        == 0
    )


def test_11_outro_tenant_nao_conta(db, default_company, cliente_exemplo, synced_catalog):
    """CorePayment de outro tenant não conta."""
    from app.models.company import Company, CompanyPlan, CompanySegment

    other = Company(
        nome="Other",
        slug="reconcile-other",
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_core_payment(
        db, other.id, booking.id, amount=Decimal("60.00")
    )
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 0
    )


def test_12_13_payment_e_core_nao_duplicam(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Mesmo valor em Payment e CorePayment não é somado duas vezes."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_payment(db, booking.id, valor=Decimal("60.00"))
    _add_core_payment(
        db, default_company.id, booking.id, amount=Decimal("60.00")
    )
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 6_000
    )


def test_14_parciais_somam(db, default_company, cliente_exemplo, synced_catalog):
    """Parcelas pagas somam no ledger."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("30.00"),
    )
    _add_payment(db, booking.id, valor=Decimal("30.00"))
    _add_payment(
        db,
        booking.id,
        valor=Decimal("30.00"),
        tipo=PaymentType.FINAL_PAYMENT,
    )
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 6_000
    )


def test_15_16_snapshot_divergente_usa_ledger(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Snapshot baixo + ledger alto → ativação usa o ledger (não reduz)."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("10.00"),  # snapshot abaixo do mínimo
    )
    _add_payment(db, booking.id, valor=Decimal("60.00"))
    updated = PaymentReservationService(db).confirmar_deposito_por_booking(
        booking.id, default_company.id
    )
    assert updated.deposit_paid is True
    # Upsert não pode ter reduzido o Payment existente
    pag = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.deleted_at.is_(None))
        .first()
    )
    assert money_to_cents(pag.valor) == 6_000


def test_17_ativacao_e_expirador_mesma_decisao(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Ativação e expirador concordam sobre o paid_cents canônico."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("100.00"),
    )
    _add_payment(db, booking.id, valor=Decimal("100.00"))
    paid = get_effective_paid_amount_cents(
        db, booking_id=booking.id, company_id=default_company.id
    )
    snap = DisponibilidadeService(db)._load_payment_activation_snapshots(
        [booking.id], company_id=default_company.id
    )[booking.id]
    assert paid == snap["paid_cents"] == 10_000
    assert paid >= calculate_minimum_activation_cents(80_000)


def test_18_falha_consulta_fail_closed(db, default_company, cliente_exemplo, synced_catalog):
    """Falha na consulta financeira → expirador fail-closed (não libera expiração)."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )

    def _boom(*_a, **_k):
        raise RuntimeError("db down")

    svc = DisponibilidadeService(db)
    svc._load_payment_activation_snapshots = _boom  # type: ignore[method-assign]
    assert svc._has_minimum_activation_payment(booking) is True


def test_20_21_teto_100_reais(db, default_company, cliente_exemplo, synced_catalog):
    """R$100 ativa serviço alto; R$99,99 não."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("99.99"),
    )
    _add_payment(db, booking.id, valor=Decimal("99.99"))
    assert (
        get_effective_paid_amount_cents(
            db, booking_id=booking.id, company_id=default_company.id
        )
        == 9_999
    )
    with pytest.raises(MinimumDepositNotMetError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    db.refresh(booking)
    assert booking.deposit_paid is False

    ok = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("100.00"),
    )
    updated = PaymentReservationService(db).confirmar_deposito_por_booking(
        ok.id, default_company.id
    )
    assert updated.deposit_paid is True


def test_abaixo_minimo_preserva_payment_sem_ativar(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Abaixo do mínimo: Payment permanece; deposit_paid permanece False."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("59.99"),
    )
    with pytest.raises(MinimumDepositNotMetError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    db.refresh(booking)
    assert booking.deposit_paid is False
    pag = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.deleted_at.is_(None))
        .first()
    )
    assert pag is not None
    assert pag.status == PaymentStatus.PAID
    assert money_to_cents(pag.valor) == 5_999


def test_processando_marca_flag(db, default_company, cliente_exemplo, synced_catalog):
    """Status processando não soma, mas marca has_processing."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _add_payment(
        db,
        booking.id,
        valor=Decimal("60.00"),
        status=PaymentStatus.PROCESSANDO,
    )
    snap = load_effective_paid_snapshots(
        db, [booking.id], company_id=default_company.id
    )[booking.id]
    assert snap.paid_cents == 0
    assert snap.has_processing is True
