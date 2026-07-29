"""
FIX-EXPIRATION-02C — protege reservas com qualquer evidência de pagamento.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

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
    Grava override de campos ``expiration.*`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        **expiration_fields: Campos de ``ExpirationPolicy``.
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
    deposit_paid: bool = False,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
    status: ReservationStatus = ReservationStatus.PENDING_PAYMENT,
    scheduled_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste booking pendente com timestamps e flags financeiras controlados.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Par catalog/offering.
        created_at: Timestamp de criação.
        deposit_paid: Sinal pago.
        payment_status: Status de pagamento.
        status: Status da reserva.
        scheduled_at: Início do slot.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at or (datetime.now() + timedelta(days=40)),
        status=status,
        payment_status=payment_status,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
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
    status: PaymentStatus = PaymentStatus.PAID,
    tipo: PaymentType = PaymentType.DEPOSIT,
) -> Payment:
    """
    Cria linha ``payments`` vinculada ao booking.

    Args:
        db: Sessão.
        booking: Booking alvo.
        status: Status do pagamento.
        tipo: Tipo (deposit/final/refund).

    Returns:
        Payment.
    """
    row = Payment(
        booking_id=booking.id,
        tipo=tipo,
        valor=booking.deposit_amount or Decimal("30.00"),
        status=status,
        paid_at=datetime.utcnow() if status in (PaymentStatus.PAID, PaymentStatus.PAGO) else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _add_core_payment(
    db,
    booking: CoreBooking,
    *,
    status: CorePaymentStatus = CorePaymentStatus.PAID,
    payment_type: CorePaymentType = CorePaymentType.DEPOSIT,
) -> CorePayment:
    """
    Cria linha ``core_payments`` vinculada ao booking.

    Args:
        db: Sessão.
        booking: Booking alvo.
        status: Status.
        payment_type: Tipo.

    Returns:
        CorePayment.
    """
    row = CorePayment(
        company_id=booking.company_id,
        booking_id=booking.id,
        payment_type=payment_type,
        amount=booking.deposit_amount or Decimal("30.00"),
        status=status,
        paid_at=datetime.utcnow() if status == CorePaymentStatus.PAID else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _outbox_expired_count(db, booking_id: int) -> int:
    """
    Conta eventos ``booking.expired`` do booking.

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


def test_01_sem_evidencia_financeira_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Sem deposit/payment_status/linhas financeiras → expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_02_deposit_paid_true_nao_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``deposit_paid=True`` protege a reserva."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=True,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.deleted_at is None
    assert _outbox_expired_count(db, booking.id) == 0


@pytest.mark.parametrize(
    "payment_status",
    [
        StatusPagamento.PARTIALLY_PAID,
        StatusPagamento.CONFIRMED,
        StatusPagamento.PAID,
    ],
)
def test_03_04_05_payment_status_protegidos(
    db,
    default_company,
    cliente_exemplo,
    synced_catalog,
    enable_booking_core,
    payment_status,
):
    """partially_paid/confirmed/paid protegem mesmo com deposit_paid=False."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=payment_status,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == payment_status
    assert booking.deleted_at is None


def test_06_payment_deposit_row_protege(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``Payment`` de entrada PAID protege com flags limpas."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    _add_payment(db, booking, status=PaymentStatus.PAID, tipo=PaymentType.DEPOSIT)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT
    assert _outbox_expired_count(db, booking.id) == 0


def test_07_core_payment_paid_protege(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``CorePayment`` PAID protege com flags limpas."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    _add_core_payment(db, booking, status=CorePaymentStatus.PAID)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_08_payment_reembolsado_permite_expirar(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Linha ``Payment`` REFUNDED não protege (estados comprovados)."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    _add_payment(db, booking, status=PaymentStatus.REFUNDED, tipo=PaymentType.DEPOSIT)
    _add_core_payment(db, booking, status=CorePaymentStatus.REFUNDED)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_09_inconsistencia_flag_e_payment_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """deposit_paid=False + payment_status pending + Payment PAID → não expira."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    _add_payment(db, booking, status=PaymentStatus.PAID, tipo=PaymentType.SINAL)
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.deleted_at is None


def test_10a_erro_pre_carga_financeira_protege_lote(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Erro na pré-carga financeira: lote inteiro fail-closed (ninguém expira)."""
    company_b = _create_company(db, "exp02c-fin-err-a")
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    def _load_boom(self, booking_ids):
        """
        Simula falha de consulta financeira em lote.

        Args:
            self: Service.
            booking_ids: IDs.

        Raises:
            RuntimeError: Sempre.
        """
        raise RuntimeError("boom financial query")

    monkeypatch.setattr(
        DisponibilidadeService,
        "_load_booking_ids_with_active_payment_rows",
        _load_boom,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.PENDING_PAYMENT


def test_10b_erro_por_booking_nao_impede_outro(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Erro ao avaliar um booking: ele não expira; outro do lote continua."""
    company_b = _create_company(db, "exp02c-fin-err-b")
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    monkeypatch.setattr(
        DisponibilidadeService,
        "_load_booking_ids_with_active_payment_rows",
        lambda self, booking_ids: set(),
    )
    real_status = DisponibilidadeService._booking_payment_status_value

    def _status_boom_a(self, booking):
        """
        Falha só ao ler payment_status do booking A.

        Args:
            self: Service.
            booking: Candidato.

        Returns:
            Status normalizado.

        Raises:
            RuntimeError: Para o booking A.
        """
        if getattr(booking, "id", None) == booking_a.id:
            raise RuntimeError("boom per booking")
        return real_status(self, booking)

    monkeypatch.setattr(
        DisponibilidadeService,
        "_booking_payment_status_value",
        _status_boom_a,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_11_require_false_com_pagamento_nao_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=false`` com pagamento parcial não expira."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False, after_hours=2)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_12_tenant_a_pago_b_sem_pagamento(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Tenant A com pagamento não expira; B sem pagamento expira."""
    company_b = _create_company(db, "exp02c-iso-pay-b")
    created = datetime.now() - timedelta(hours=5)
    paid_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        deposit_paid=False,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    unpaid_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(paid_a)
    db.refresh(unpaid_b)
    assert paid_a.status == ReservationStatus.PENDING_PAYMENT
    assert unpaid_b.status == ReservationStatus.EXPIRED


def test_13_14_15_payment_intact_deleted_outbox(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Protegido: payment intacto, sem deleted_at, sem outbox expired."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking.deleted_at is None
    assert _outbox_expired_count(db, booking.id) == 0


def test_16_regressao_enabled_after_hours_reference_eligible(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Regressão 01/02A/02B com proteção financeira ativa."""
    company_b = _create_company(db, "exp02c-reg2-b")
    _upsert_expiration(db, default_company.id, enabled=False, after_hours=2)
    _upsert_expiration(
        db,
        company_b.id,
        reference="scheduled_at",
        eligible_statuses=["pending_payment"],
        after_hours=2,
    )

    created_old = datetime.now() - timedelta(hours=5)
    booking_disabled = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created_old
    )
    booking_future = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        scheduled_at=datetime.now() + timedelta(days=3),
    )
    booking_past = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=5),
        scheduled_at=datetime.now() - timedelta(hours=5),
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_disabled)
    db.refresh(booking_future)
    db.refresh(booking_past)
    assert booking_disabled.status == ReservationStatus.PENDING_PAYMENT
    assert booking_future.status == ReservationStatus.PENDING_PAYMENT
    assert booking_past.status == ReservationStatus.EXPIRED


def test_17_sem_company_id_fail_closed(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Booking sem ``company_id`` é ignorado; outro do lote ainda expira."""
    from app.modules.booking.domain.models import CoreBooking as CB

    booking_ok = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
    )
    fake = SimpleNamespace(
        id=9_999_993,
        company_id=None,
        created_at=datetime.now() - timedelta(hours=10),
        scheduled_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        deleted_at=None,
    )

    real_query = db.query
    injected = {"done": False}

    def query_proxy(model):
        """
        Injeta booking sem tenant nos candidatos de CoreBooking.

        Args:
            model: Modelo SQLAlchemy.

        Returns:
            Query possivelmente monkeypatched.
        """
        q = real_query(model)
        if model is CB and not injected["done"]:
            original_all = q.all

            def all_with_fake():
                """
                Retorna candidatos + fake.

                Returns:
                    Lista.
                """
                injected["done"] = True
                return list(original_all()) + [fake]

            q.all = all_with_fake  # type: ignore[method-assign]
        return q

    monkeypatch.setattr(db, "query", query_proxy)
    count = DisponibilidadeService(db).expirar_reservas_pendentes()
    assert count >= 1
    db.refresh(booking_ok)
    assert booking_ok.status == ReservationStatus.EXPIRED


def test_require_true_unpaid_ainda_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=true`` sem evidência financeira continua expirando."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=True, after_hours=2)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT
