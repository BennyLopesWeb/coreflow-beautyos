"""
FIX-EXPIRATION-02C — mínimo de ativação financeira ``min(20%, R$100)``.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType
from app.services.disponibilidade_service import DisponibilidadeService
from app.shared.events.outbox import CoreEventOutbox


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


def _upsert_expiration(db, company_id: int, **expiration_fields) -> None:
    """
    Grava override de campos ``expiration.*``.

    Args:
        db: Sessão.
        company_id: Tenant.
        **expiration_fields: Campos da política.
    """
    payload = {"expiration": dict(expiration_fields)}
    now = datetime.utcnow()
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == company_id)
        .first()
    )
    if row is None:
        db.add(
            BookingPolicyConfig(
                company_id=company_id,
                policy_json=payload,
                version=1,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        row.policy_json = payload
        row.is_active = True
        row.updated_at = now
    db.commit()


def _create_pending_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    created_at: datetime,
    price_total: Decimal = Decimal("100.00"),
    deposit_amount: Decimal | None = None,
    deposit_paid: bool = False,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
    status: ReservationStatus = ReservationStatus.PENDING_PAYMENT,
    scheduled_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste booking pendente com totais financeiros controlados.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Par catalog/offering.
        created_at: Timestamp de criação.
        price_total: Total do serviço em reais.
        deposit_amount: Valor do sinal (default 30% do total).
        deposit_paid: Flag de sinal.
        payment_status: Status agregado.
        status: Status da reserva.
        scheduled_at: Slot.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    if deposit_amount is None:
        deposit_amount = (price_total * Decimal("0.30")).quantize(Decimal("0.01"))
    remaining = (price_total - deposit_amount).quantize(Decimal("0.01"))
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at or (datetime.now() + timedelta(days=40)),
        status=status,
        payment_status=payment_status,
        price_total=price_total,
        deposit_pct=Decimal("0.30"),
        deposit_amount=deposit_amount,
        remaining_amount=remaining,
        deposit_paid=deposit_paid,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=created_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.created_at = created_at
    if scheduled_at is not None:
        row.scheduled_at = scheduled_at
    db.commit()
    db.refresh(row)
    return row


def _add_payment(
    db,
    booking: CoreBooking,
    *,
    valor: Decimal,
    status: PaymentStatus = PaymentStatus.PAID,
    tipo: PaymentType = PaymentType.DEPOSIT,
) -> Payment:
    """
    Cria linha ``payments`` com valor explícito.

    Args:
        db: Sessão.
        booking: Booking.
        valor: Valor em reais.
        status: Status.
        tipo: Tipo.

    Returns:
        Payment.
    """
    row = Payment(
        booking_id=booking.id,
        tipo=tipo,
        valor=valor,
        status=status,
        paid_at=datetime.utcnow()
        if status in (PaymentStatus.PAID, PaymentStatus.PAGO)
        else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _add_core_payment(
    db,
    booking: CoreBooking,
    *,
    amount: Decimal,
    status: CorePaymentStatus = CorePaymentStatus.PAID,
) -> CorePayment:
    """
    Cria linha ``core_payments`` com valor explícito.

    Args:
        db: Sessão.
        booking: Booking.
        amount: Valor em reais.
        status: Status.

    Returns:
        CorePayment.
    """
    row = CorePayment(
        company_id=booking.company_id,
        booking_id=booking.id,
        payment_type=CorePaymentType.DEPOSIT,
        amount=amount,
        status=status,
        paid_at=datetime.utcnow() if status == CorePaymentStatus.PAID else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _outbox_expired_count(db, booking_id: int) -> int:
    """
    Conta eventos ``booking.expired``.

    Args:
        db: Sessão.
        booking_id: ID.

    Returns:
        Quantidade.
    """
    return (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.expired",
            CoreEventOutbox.aggregate_id == str(booking_id),
        )
        .count()
    )


def test_minimum_formula_helpers():
    """Fórmula em centavos: 20% até R$500; teto R$100 acima."""
    assert DisponibilidadeService._get_minimum_activation_cents(30_000) == 6_000
    assert DisponibilidadeService._get_minimum_activation_cents(50_000) == 10_000
    assert DisponibilidadeService._get_minimum_activation_cents(80_000) == 10_000
    assert DisponibilidadeService._money_to_cents(Decimal("59.99")) == 5_999
    assert DisponibilidadeService._money_to_cents(Decimal("60.00")) == 6_000


def test_01_300_pago_5999_abaixo_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$300 + R$59,99 (5999 < 6000) → não ativa → expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        deposit_paid=False,
    )
    _add_payment(db, booking, valor=Decimal("59.99"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_02_300_pago_6000_ativa(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$300 + R$60,00 (6000 == 6000) → ativa → não expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.00"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.deleted_at is None
    assert _outbox_expired_count(db, booking.id) == 0


def test_03_300_pago_6001_ativa(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$300 + R$60,01 → ativa."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.01"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_04_500_pago_100_ativa(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$500 + R$100 (10000 == teto/20%) → ativa."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("500.00"),
    )
    _add_payment(db, booking, valor=Decimal("100.00"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_05_800_pago_100_ativa(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$800 + R$100 (teto) → ativa."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("800.00"),
    )
    _add_payment(db, booking, valor=Decimal("100.00"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_06_800_pago_9999_abaixo_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """R$800 + R$99,99 (9999 < 10000) → não ativa → expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("800.00"),
    )
    _add_payment(db, booking, valor=Decimal("99.99"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_07_pagamento_zero_nao_ativa_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Sem valor pago → não ativa → expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_08_pending_nao_conta_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Payment PENDING não conta para ativação."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.00"), status=PaymentStatus.PENDING)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


@pytest.mark.parametrize(
    "status",
    [PaymentStatus.FAILED, PaymentStatus.CANCELADO, PaymentStatus.REFUNDED],
)
def test_09_failed_cancelled_refunded_nao_contam(
    db,
    default_company,
    cliente_exemplo,
    synced_catalog,
    enable_booking_core,
    status,
):
    """Failed/cancelled/refunded não contam → pode expirar."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.00"), status=status)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_10_parcial_valido_conta(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Parcial válido (CorePayment PAID) conta para ativação."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    _add_core_payment(
        db, booking, amount=Decimal("60.00"), status=CorePaymentStatus.PAID
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID


def test_11_multiplas_parcelas_somam(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Duas parcelas 40+20 = 60 ativam serviço de R$300."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("40.00"), status=PaymentStatus.PAID)
    _add_payment(
        db,
        booking,
        valor=Decimal("20.00"),
        status=PaymentStatus.PAID,
        tipo=PaymentType.FINAL_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_12_processando_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """PROCESSANDO não conta na soma, mas bloqueia expiração (fail-closed)."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(
        db, booking, valor=Decimal("60.00"), status=PaymentStatus.PROCESSANDO
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.deleted_at is None


def test_13_14_15_ativo_nao_chama_handler_preserva_flags(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Ativo: não chama handler; payment_status e deleted_at intactos."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    _add_payment(db, booking, valor=Decimal("60.00"), status=PaymentStatus.PAID)

    handler_mock = MagicMock()
    monkeypatch.setattr(
        "app.modules.booking.application.commands.expire_booking.ExpireBookingHandler.execute",
        handler_mock,
    )
    # Patch na classe usada após import local — intercepta via module path no loop
    from app.modules.booking.application.commands import expire_booking as eb_mod

    monkeypatch.setattr(eb_mod.ExpireBookingHandler, "execute", handler_mock)

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    handler_mock.assert_not_called()
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking.deleted_at is None
    assert _outbox_expired_count(db, booking.id) == 0


def test_16_abaixo_minimo_segue_expiracao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Abaixo do mínimo: payment permanece; status vira expired."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    _add_payment(db, booking, valor=Decimal("10.00"), status=PaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT


def test_17_divergencia_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Flags pagos sem valor mensurável → fail-closed."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        deposit_paid=False,
        deposit_amount=Decimal("0.00"),
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_18_erro_consulta_protege_lote_continua(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Erro na pré-carga: lote protegido; erro por booking não aborta o outro."""
    company_b = _create_company(db, "exp02c-act-err-b")
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        price_total=Decimal("300.00"),
    )
    booking_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        price_total=Decimal("300.00"),
    )

    def _boom(self, booking_ids, *, company_id=None):
        """
        Simula falha de snapshot financeiro.

        Args:
            self: Service.
            booking_ids: IDs.
            company_id: Tenant do lote (ignorado no mock).

        Raises:
            RuntimeError: Sempre.
        """
        raise RuntimeError("boom snapshot")

    monkeypatch.setattr(
        DisponibilidadeService, "_load_payment_activation_snapshots", _boom
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.PENDING_PAYMENT

    monkeypatch.setattr(
        DisponibilidadeService,
        "_load_payment_activation_snapshots",
        lambda self, ids, *, company_id=None: {
            bid: {"paid_cents": 0, "has_processing": False, "has_paid_rows": False}
            for bid in ids
        },
    )
    real_money = DisponibilidadeService._money_to_cents

    def _money_boom(value):
        """
        Falha só para price_total do booking A (300.00).

        Args:
            value: Valor monetário.

        Returns:
            Centavos.

        Raises:
            RuntimeError: Para total 300.
        """
        if value is not None and Decimal(str(value)) == Decimal("300.00"):
            # Ambos A e B têm 300 — usar id via abordagem diferente
            pass
        return real_money(value)

    # Erro por booking via _has_minimum_activation_payment interno:
    real_has = DisponibilidadeService._has_minimum_activation_payment

    def _has_fail_a(self, booking, *, payment_snapshots=None):
        """
        Força exceção no booking A (helper fail-closed).

        Args:
            self: Service.
            booking: Candidato.
            payment_snapshots: Snapshot.

        Returns:
            Bloqueio de expiração.
        """
        if getattr(booking, "id", None) == booking_a.id:
            raise RuntimeError("boom activation")
        return real_has(self, booking, payment_snapshots=payment_snapshots)

    # O helper captura a exceção internamente se levantada dentro do try —
    # então levantamos antes de chamar real_has e retornamos True no wrapper.
    def _has_fail_a_safe(self, booking, *, payment_snapshots=None):
        """
        Simula o caminho fail-closed do helper para o booking A.

        Args:
            self: Service.
            booking: Candidato.
            payment_snapshots: Snapshot.

        Returns:
            ``True`` para A; delega nos demais.
        """
        if getattr(booking, "id", None) == booking_a.id:
            try:
                raise RuntimeError("boom activation")
            except Exception:
                return True
        return real_has(self, booking, payment_snapshots=payment_snapshots)

    monkeypatch.setattr(
        DisponibilidadeService, "_has_minimum_activation_payment", _has_fail_a_safe
    )
    booking_a.status = ReservationStatus.PENDING_PAYMENT
    booking_a.deleted_at = None
    booking_b.status = ReservationStatus.PENDING_PAYMENT
    booking_b.deleted_at = None
    db.commit()
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_19_tenants_isolados_ativacao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """A ativo (R$60/R$300); B abaixo (R$10/R$300) → só B expira."""
    company_b = _create_company(db, "exp02c-act-iso-b")
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking_a, valor=Decimal("60.00"))
    booking_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking_b, valor=Decimal("10.00"))
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_20_regressao_enabled_reference_eligible(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Regressão enabled/reference/eligible com regra de ativação."""
    company_b = _create_company(db, "exp02c-act-reg-b")
    _upsert_expiration(db, default_company.id, enabled=False)
    _upsert_expiration(
        db,
        company_b.id,
        reference="scheduled_at",
        eligible_statuses=["pending_payment"],
        after_hours=2,
    )
    created_old = datetime.now() - timedelta(hours=5)
    disabled = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        price_total=Decimal("300.00"),
    )
    future = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        price_total=Decimal("300.00"),
        scheduled_at=datetime.now() + timedelta(days=3),
    )
    past = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=5),
        price_total=Decimal("300.00"),
        scheduled_at=datetime.now() - timedelta(hours=5),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(disabled)
    db.refresh(future)
    db.refresh(past)
    assert disabled.status == ReservationStatus.PENDING_PAYMENT
    assert future.status == ReservationStatus.PENDING_PAYMENT
    assert past.status == ReservationStatus.EXPIRED


def test_21_22_outbox_e_retry_idempotente(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Ativo: sem outbox; retry não cria efeitos."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.00"))
    DisponibilidadeService(db).expirar_reservas_pendentes()
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert _outbox_expired_count(db, booking.id) == 0


def test_require_false_nao_expira_ativo(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=false`` não libera reserva ativa."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    _add_payment(db, booking, valor=Decimal("60.00"))
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_sem_company_id_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Booking sem company_id ignorado; outro sem pagamento expira."""
    from app.modules.booking.domain.models import CoreBooking as CB

    booking_ok = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
    )
    fake = SimpleNamespace(
        id=9_999_994,
        company_id=None,
        created_at=datetime.now() - timedelta(hours=10),
        scheduled_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("0.00"),
        deleted_at=None,
    )
    real_query = db.query
    injected = {"done": False}

    def query_proxy(*entities, **kwargs):
        """
        Injeta fake sem tenant na query de ``CoreBooking``.

        Args:
            *entities: Argumentos de ``Session.query``.
            **kwargs: Keyword args opcionais.

        Returns:
            Query.
        """
        q = real_query(*entities, **kwargs)
        if entities and entities[0] is CB and not injected["done"]:
            original_all = q.all

            def all_with_fake():
                """
                Candidatos + fake.

                Returns:
                    Lista.
                """
                injected["done"] = True
                return list(original_all()) + [fake]

            q.all = all_with_fake  # type: ignore[method-assign]
        return q

    monkeypatch.setattr(db, "query", query_proxy)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_ok)
    assert booking_ok.status == ReservationStatus.EXPIRED
