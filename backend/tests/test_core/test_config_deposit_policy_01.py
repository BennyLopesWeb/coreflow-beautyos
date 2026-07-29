"""
CONFIG-DEPOSIT-POLICY-01 — política de entrada configurável por tenant.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError, MinimumDepositNotMetError, ValidationError
from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    resolve_booking_minimum_activation_cents,
)
from app.modules.booking.domain.policy.models import BookingPolicyAudit, BookingPolicyConfig
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.modules.booking.domain.policy.schemas import ActivationPolicy
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.company_service import CompanyService
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService


def _admin(db, email: str, company: Company) -> User:
    """
    Cria admin do tenant.

    Args:
        db: Sessão.
        email: E-mail.
        company: Empresa.

    Returns:
        User.
    """
    user = User(
        email=email,
        hashed_password=get_password_hash("x"),
        nome="Admin",
        ativo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    CompanyService(db).assign_user(user, company, CompanyRole.OWNER)
    return user


def _headers(user: User, company: Company) -> dict:
    """
    Headers Bearer admin.

    Args:
        user: Usuário.
        company: Tenant.

    Returns:
        Dict Authorization.
    """
    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "company_id": company.id,
            "role": "owner",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _company(db, slug: str) -> Company:
    """
    Cria empresa auxiliar.

    Args:
        db: Sessão.
        slug: Slug único.

    Returns:
        Company.
    """
    c = Company(
        nome=slug,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _booking(db, company, cliente, synced_catalog, *, price_total, deposit_amount=None):
    """
    Cria booking pendente sem snapshot (legado).

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Fixture.
        price_total: Total.
        deposit_amount: Cotação.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    dep = deposit_amount if deposit_amount is not None else (price_total * Decimal("0.30"))
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.utcnow() + timedelta(days=7),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price_total,
        deposit_amount=dep,
        remaining_amount=(price_total - dep).quantize(Decimal("0.01")),
        deposit_paid=False,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _pay(db, booking_id, valor):
    """
    Insere Payment PAID.

    Args:
        db: Sessão.
        booking_id: Booking.
        valor: Valor.

    Returns:
        Payment.
    """
    pag = Payment(
        booking_id=booking_id,
        tipo=PaymentType.DEPOSIT,
        valor=valor,
        status=PaymentStatus.PAID,
        paid_at=datetime.utcnow(),
    )
    db.add(pag)
    db.commit()
    return pag


def test_fallback_legado_equivalente():
    """Sem política tipada: 20% com teto 10000."""
    assert calculate_minimum_activation_cents(30_000) == 6_000
    assert calculate_minimum_activation_cents(80_000) == 10_000


def test_percentage_with_cap_arredondamento_e_teto():
    """Modo percentage_with_cap: ceil e teto."""
    pol = ActivationPolicy(
        mode="percentage_with_cap",
        currency="BRL",
        percentage=20,
        cap_cents=10_000,
    )
    assert calculate_minimum_activation_cents(333, activation=pol) == 67  # ceil
    assert calculate_minimum_activation_cents(80_000, activation=pol) == 10_000


def test_tiered_limiar_e_um_centavo_abaixo():
    """Faixa: limiar exato usa high; um centavo abaixo usa standard."""
    pol = ActivationPolicy(
        mode="tiered_percentage",
        currency="BRL",
        standard_percentage=20,
        high_value_threshold_cents=50_000,
        high_value_percentage=30,
        cap_cents=None,
    )
    assert calculate_minimum_activation_cents(49_999, activation=pol) == (
        49_999 * 20 + 99
    ) // 100
    assert calculate_minimum_activation_cents(50_000, activation=pol) == (
        50_000 * 30 + 99
    ) // 100


def test_percentual_zero_explicito():
    """Percentual zero explícito gera mínimo 0."""
    pol = ActivationPolicy(
        mode="percentage_with_cap",
        currency="BRL",
        percentage=0,
        cap_cents=10_000,
    )
    assert calculate_minimum_activation_cents(30_000, activation=pol) == 0


def test_config_invalida_rejeitada_no_schema():
    """high_value < standard é inválido."""
    with pytest.raises(PydanticValidationError):
        ActivationPolicy(
            mode="tiered_percentage",
            currency="BRL",
            standard_percentage=30,
            high_value_threshold_cents=50_000,
            high_value_percentage=20,
            cap_cents=None,
        )


def test_admin_activation_isolamento_auditoria_e_version(
    client, db, default_company
):
    """PUT activation isola tenant, audita e bumpa version; 409 em expected_version."""
    other = _company(db, "cdp01-other")
    admin_a = _admin(db, "cdp01-a@test.local", default_company)
    admin_b = _admin(db, "cdp01-b@test.local", other)

    resp_b = client.put(
        "/admin/booking-policy",
        json={
            "activation": {
                "mode": "tiered_percentage",
                "currency": "BRL",
                "standard_percentage": 20,
                "high_value_threshold_cents": 50_000,
                "high_value_percentage": 30,
                "cap_cents": None,
            },
            "reason": "tiered B",
        },
        headers=_headers(admin_b, other),
    )
    assert resp_b.status_code == 200, resp_b.text
    assert resp_b.json()["version"] == 1

    resp_a = client.get(
        "/admin/booking-policy", headers=_headers(admin_a, default_company)
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["policy"]["activation"]["mode"] == "percentage_with_cap"
    assert resp_a.json()["policy"]["activation"]["percentage"] == 20

    put_a = client.put(
        "/admin/booking-policy",
        json={
            "activation": {
                "mode": "percentage_with_cap",
                "currency": "BRL",
                "percentage": 25,
                "cap_cents": 8_000,
            },
            "reason": "cap A",
        },
        headers=_headers(admin_a, default_company),
    )
    assert put_a.status_code == 200, put_a.text
    assert put_a.json()["version"] == 1
    assert put_a.json()["policy"]["activation"]["percentage"] == 25

    conflict = client.patch(
        "/admin/booking-policy",
        json={
            "activation": {
                "mode": "percentage_with_cap",
                "currency": "BRL",
                "percentage": 10,
                "cap_cents": 10_000,
            },
            "expected_version": 99,
            "reason": "conflito",
        },
        headers=_headers(admin_a, default_company),
    )
    assert conflict.status_code == 409, conflict.text

    audits = (
        db.query(BookingPolicyAudit)
        .filter(BookingPolicyAudit.company_id == default_company.id)
        .count()
    )
    assert audits >= 1


def test_admin_config_invalida_nao_persiste(client, db, default_company):
    """Config inválida → 422 sem bump de versão."""
    admin = _admin(db, "cdp01-bad@test.local", default_company)
    resp = client.put(
        "/admin/booking-policy",
        json={
            "activation": {
                "mode": "percentage_with_cap",
                "currency": "BRL",
                "percentage": 20,
                # cap_cents ausente
            },
            "reason": "invalido",
        },
        headers=_headers(admin, default_company),
    )
    assert resp.status_code == 422, resp.text
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == default_company.id)
        .first()
    )
    assert row is None


def test_snapshot_imutavel_apos_mudanca_de_politica(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Alteração posterior da policy não muda booking existente."""
    from app.modules.booking.domain.policy.activation_persist import (
        persist_activation_snapshot_on_booking,
    )

    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"),
    )
    persist_activation_snapshot_on_booking(
        db,
        booking_id=booking.id,
        company_id=default_company.id,
        price_total=booking.price_total,
    )
    db.commit()
    db.refresh(booking)
    assert booking.minimum_activation_cents == 6_000
    original_snap = dict(booking.activation_policy_snapshot)

    now = datetime.utcnow()
    db.add(
        BookingPolicyConfig(
            company_id=default_company.id,
            policy_json={
                "activation": {
                    "mode": "percentage_with_cap",
                    "currency": "BRL",
                    "percentage": 50,
                    "cap_cents": 50_000,
                }
            },
            version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    db.refresh(booking)
    assert resolve_booking_minimum_activation_cents(booking) == 6_000
    assert booking.activation_policy_snapshot == original_snap


def test_booking_legado_usa_formula_hardcoded(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Sem snapshot → sempre legado, mesmo com override atual."""
    now = datetime.utcnow()
    db.add(
        BookingPolicyConfig(
            company_id=default_company.id,
            policy_json={
                "activation": {
                    "mode": "percentage_with_cap",
                    "currency": "BRL",
                    "percentage": 50,
                    "cap_cents": 50_000,
                }
            },
            version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"),
    )
    assert booking.minimum_activation_cents is None
    assert resolve_booking_minimum_activation_cents(booking) == 6_000


def test_ativacao_usa_snapshot_e_ledger(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Ativação compara ledger com mínimo do snapshot."""
    from app.modules.booking.domain.policy.activation_persist import (
        persist_activation_snapshot_on_booking,
    )

    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"),
    )
    persist_activation_snapshot_on_booking(
        db,
        booking_id=booking.id,
        company_id=default_company.id,
    )
    db.commit()
    _pay(db, booking.id, Decimal("59.99"))
    with pytest.raises(MinimumDepositNotMetError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )
    _pay(db, booking.id, Decimal("0.01"))
    updated = PaymentReservationService(db).confirmar_deposito_por_booking(
        booking.id, default_company.id
    )
    assert updated.deposit_paid is True


def test_expirador_respeita_snapshot(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Expirador usa mínimo do snapshot (não config atual)."""
    from app.modules.booking.domain.policy.activation_persist import (
        persist_activation_snapshot_on_booking,
    )

    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"),
    )
    persist_activation_snapshot_on_booking(
        db,
        booking_id=booking.id,
        company_id=default_company.id,
    )
    db.commit()
    _pay(db, booking.id, Decimal("60.00"))
    assert DisponibilidadeService(db)._has_minimum_activation_payment(booking) is True


def test_processing_e_divergencia_preservados(
    db, default_company, cliente_exemplo, synced_catalog
):
    """PR #41: processing e divergência ainda bloqueiam."""
    from app.modules.booking.domain.policy.activation_persist import (
        persist_activation_snapshot_on_booking,
    )
    from app.modules.payments.models import CorePayment, CorePaymentStatus, CorePaymentType

    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog,
        price_total=Decimal("300.00"),
    )
    persist_activation_snapshot_on_booking(
        db, booking_id=booking.id, company_id=default_company.id
    )
    db.commit()

    db.add(
        Payment(
            booking_id=booking.id,
            tipo=PaymentType.DEPOSIT,
            valor=Decimal("60.00"),
            status=PaymentStatus.PROCESSANDO,
        )
    )
    db.commit()
    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )

    db.query(Payment).filter(Payment.booking_id == booking.id).delete()
    db.commit()
    _pay(db, booking.id, Decimal("60.00"))
    db.add(
        CorePayment(
            company_id=default_company.id,
            booking_id=booking.id,
            payment_type=CorePaymentType.DEPOSIT,
            amount=Decimal("50.00"),
            status=CorePaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()
    with pytest.raises(ValidationError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, default_company.id
        )


def test_defaults_incluem_activation(db, default_company):
    """Resolver inclui grupo activation com default 20/10000."""
    policy = BookingPolicyResolver(db).resolve(default_company.id)
    assert policy.activation.mode == "percentage_with_cap"
    assert policy.activation.percentage == 20
    assert policy.activation.cap_cents == 10_000
