"""
FIX-EXPIRATION-02C — ``require_unpaid_deposit=false`` não expira depósito pago.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
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


def _upsert_expiration(db, company_id: int, **expiration_fields) -> None:
    """
    Grava override de campos ``expiration.*`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        **expiration_fields: Campos de ``ExpirationPolicy`` a sobrescrever.
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


def test_01_require_true_unpaid_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=true`` + ``deposit_paid=False`` continua expirando."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=True, after_hours=2)
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
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT


def test_02_require_true_paid_nao_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=true`` + ``deposit_paid=True`` não expira."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=True, after_hours=2)
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
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking.deposit_paid is True


def test_03_require_false_paid_nao_expira_trava(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=false`` + depósito pago: trava — não expira."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False, after_hours=2)
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
    assert booking.status == ReservationStatus.PENDING_PAYMENT
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking.deposit_paid is True
    assert booking.deleted_at is None


def test_04_require_false_unpaid_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=false`` + ``deposit_paid=False`` segue expirando."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False, after_hours=2)
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
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT


def test_05_payment_status_intacto_em_todos_cenarios(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``payment_status`` permanece intacto com e sem expiração."""
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False, after_hours=2)
    unpaid = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    paid = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(unpaid)
    db.refresh(paid)
    assert unpaid.payment_status == StatusPagamento.PENDING_PAYMENT
    assert paid.payment_status == StatusPagamento.PARTIALLY_PAID


def test_06_tenants_require_flags_isolados(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Tenants A/B com flags diferentes de ``require_unpaid_deposit`` isolados."""
    company_b = _create_company(db, "exp02c-iso-b")
    _upsert_expiration(db, default_company.id, require_unpaid_deposit=False, after_hours=2)
    _upsert_expiration(db, company_b.id, require_unpaid_deposit=True, after_hours=2)

    created = datetime.now() - timedelta(hours=5)
    paid_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    unpaid_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        deposit_paid=False,
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(paid_a)
    db.refresh(unpaid_b)
    assert paid_a.status == ReservationStatus.PENDING_PAYMENT
    assert unpaid_b.status == ReservationStatus.EXPIRED


def test_07_regressao_enabled_after_hours_reference_eligible(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Regressão 01/02A/02B: enabled, after_hours, reference, eligible_statuses."""
    company_b = _create_company(db, "exp02c-reg-b")
    _upsert_expiration(
        db,
        default_company.id,
        enabled=False,
        require_unpaid_deposit=False,
        after_hours=2,
    )
    _upsert_expiration(
        db,
        company_b.id,
        reference="scheduled_at",
        eligible_statuses=["pending_payment"],
        after_hours=2,
        require_unpaid_deposit=True,
    )

    created_old = datetime.now() - timedelta(hours=5)
    booking_disabled = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        deposit_paid=False,
    )
    booking_future_slot = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        scheduled_at=datetime.now() + timedelta(days=3),
        deposit_paid=False,
    )
    booking_past_slot = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=5),
        scheduled_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_disabled)
    db.refresh(booking_future_slot)
    db.refresh(booking_past_slot)
    assert booking_disabled.status == ReservationStatus.PENDING_PAYMENT
    assert booking_future_slot.status == ReservationStatus.PENDING_PAYMENT
    assert booking_past_slot.status == ReservationStatus.EXPIRED
