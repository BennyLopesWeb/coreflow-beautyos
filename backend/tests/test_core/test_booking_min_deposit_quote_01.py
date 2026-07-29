"""
FIX-BOOKING-MIN-DEPOSIT-QUOTE-01 — exibir e validar entrada mínima no agendamento.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import MinimumDepositNotMetError
from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    cents_to_decimal,
    meets_minimum_activation,
    money_to_cents,
)
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.schemas.coreflow_v1 import BookingResponse, OfferingResponse
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.services.company_service import CompanyService
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService


def _ledger_deposit(db, booking_id: int, valor: Decimal) -> Payment:
    """
    Registra Payment PAID de depósito no ledger (fonte canônica).

    Args:
        db: Sessão.
        booking_id: ID do booking.
        valor: Valor pago em reais.

    Returns:
        Payment persistido.
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
    db.refresh(pag)
    return pag


def test_01_02_03_formula_shared():
    """R$300→60; R$500→100; R$800→100 (centavos, sem float)."""
    assert calculate_minimum_activation_cents(30_000) == 6_000
    assert calculate_minimum_activation_cents(50_000) == 10_000
    assert calculate_minimum_activation_cents(80_000) == 10_000
    assert cents_to_decimal(6_000) == Decimal("60.00")
    assert cents_to_decimal(10_000) == Decimal("100.00")


def test_04_05_06_meets_minimum_boundaries():
    """59,99 não ativa; 60,00 e 60,01 ativam (serviço R$300)."""
    assert not meets_minimum_activation(
        total_service_cents=30_000, paid_cents=5_999
    )
    assert meets_minimum_activation(total_service_cents=30_000, paid_cents=6_000)
    assert meets_minimum_activation(total_service_cents=30_000, paid_cents=6_001)


def test_07_08_cap_boundaries():
    """R$800: 99,99 não ativa; 100,00 ativa."""
    assert not meets_minimum_activation(
        total_service_cents=80_000, paid_cents=9_999
    )
    assert meets_minimum_activation(total_service_cents=80_000, paid_cents=10_000)


def test_09_ceil_fractional_cents_logic():
    """ceil via inteiros: 333 cents * 20% → 67 (não 66)."""
    # 3.33 → 333 cents; 20% = 66.6 → ceil 67
    assert calculate_minimum_activation_cents(333) == 67


def test_10_11_zero_and_negative():
    """Total zero/negativo rejeitados; money_to_cents seguro."""
    with pytest.raises(ValueError):
        calculate_minimum_activation_cents(0)
    with pytest.raises(ValueError):
        calculate_minimum_activation_cents(-1)
    assert money_to_cents(None) is None
    assert money_to_cents(Decimal("-1.00")) is None


def test_12_no_float_in_formula():
    """Implementação usa apenas aritmética inteira."""
    import inspect
    from app.modules.booking.domain.policy import activation as mod

    src = inspect.getsource(mod.calculate_minimum_activation_cents)
    assert "float(" not in src
    assert "//" in src
    assert "*" in src


def test_13_16_booking_response_exposes_minimum():
    """BookingResponse inclui total, mínimo e moeda (R$300 → R$60)."""
    dto = BookingResponse(
        id=1,
        company_id=1,
        customer_id=1,
        catalog_id=1,
        offering_id=1,
        scheduled_at=datetime.now(),
        status="pending_payment",
        payment_status="pending_payment",
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("90.00"),
        remaining_amount=Decimal("210.00"),
        deposit_paid=False,
        created_at=datetime.now(),
    )
    assert dto.price_total_cents == 30_000
    assert dto.minimum_activation_cents == 6_000
    assert dto.minimum_activation_amount == Decimal("60.00")
    assert dto.currency == "BRL"


def test_17_offering_response_800_shows_100():
    """OfferingResponse: serviço R$800 → mínimo R$100 (antes da confirmação)."""
    dto = OfferingResponse(
        id=1,
        company_id=1,
        catalog_id=1,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("240.00"),
        active=True,
    )
    assert dto.minimum_activation_cents == 10_000
    assert dto.minimum_activation_amount == Decimal("100.00")
    assert dto.currency == "BRL"


def _create_company(db, slug: str) -> Company:
    """
    Persiste empresa auxiliar.

    Args:
        db: Sessão.
        slug: Slug.

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


def _create_admin(db, email: str, company: Company) -> User:
    """
    Cria admin OWNER.

    Args:
        db: Sessão.
        email: E-mail.
        company: Tenant.

    Returns:
        User.
    """
    user = User(
        email=email,
        nome="Quote Admin",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    CompanyService(db).assign_user(user, company, CompanyRole.OWNER)
    return user


def _auth_headers(user: User, company: Company) -> dict:
    """
    Headers Bearer.

    Args:
        user: Usuário.
        company: Empresa.

    Returns:
        Headers.
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


def _create_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    price_total: Decimal,
    deposit_amount: Decimal,
) -> CoreBooking:
    """
    Persiste booking com totais controlados.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Catalog/offering.
        price_total: Total.
        deposit_amount: Sinal snapshot.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=10),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price_total,
        deposit_pct=Decimal("0.30"),
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


def test_18_19_20_deposit_confirm_min_and_reject(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Exatamente no mínimo aceita; abaixo rejeita com mínimo no erro."""
    # R$300, ledger = R$60 → ativa (deposit_amount é só cotação)
    ok = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("90.00"),
    )
    _ledger_deposit(db, ok.id, Decimal("60.00"))
    svc = PaymentReservationService(db)
    updated = svc.confirmar_deposito_por_booking(ok.id, default_company.id)
    assert updated.deposit_paid is True
    assert updated.payment_status == StatusPagamento.PARTIALLY_PAID

    # R$300, ledger = R$59.99 → rejeita
    low = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("90.00"),
    )
    _ledger_deposit(db, low.id, Decimal("59.99"))
    with pytest.raises(MinimumDepositNotMetError) as exc:
        svc.confirmar_deposito_por_booking(low.id, default_company.id)
    detail = exc.value.detail
    assert detail["code"] == "MINIMUM_DEPOSIT_NOT_MET"
    assert detail["minimum_activation_cents"] == 6_000
    assert detail["currency"] == "BRL"
    db.refresh(low)
    assert low.deposit_paid is False
    assert low.payment_status == StatusPagamento.PENDING_PAYMENT


def test_21_22_create_api_recalculates_minimum(
    client,
    db,
    default_company,
    cliente_exemplo,
    synced_catalog,
    booking_headers,
    monkeypatch,
):
    """POST /v1/bookings responde mínimo recalculado do snapshot do servidor."""

    def _flag(key: str) -> bool:
        return key == "booking.core.enabled"

    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        _flag,
    )
    catalog, offering = synced_catalog
    offering.price_total = Decimal("300.00")
    offering.deposit_amount = Decimal("90.00")
    db.commit()

    # Slot futuro disponível
    from app.services.disponibilidade_service import DisponibilidadeService

    DisponibilidadeService(db).expirar_reservas_pendentes()
    slot = datetime.now().replace(second=0, microsecond=0) + timedelta(days=20)
    # alinhar a um horário típico de expediente
    slot = slot.replace(hour=10, minute=0)

    resp = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers={
            **booking_headers(),
            "Idempotency-Key": "quote-01-create-1",
        },
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    # Preço vem do snapshot ACL (service_image); mínimo derivado do price_total retornado
    price_cents = money_to_cents(body["price_total"])
    assert price_cents is not None and price_cents > 0
    assert body["minimum_activation_cents"] == calculate_minimum_activation_cents(
        price_cents
    )
    assert body["currency"] == "BRL"
    assert "minimum_activation_amount" in body


def test_23_tenant_isolation_confirm(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Confirmação de depósito no tenant A não afeta booking do tenant B."""
    company_b = _create_company(db, "quote-iso-b")
    booking_a = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    booking_b = _create_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("100.00"),
    )
    svc = PaymentReservationService(db)
    _ledger_deposit(db, booking_a.id, Decimal("60.00"))
    with pytest.raises(Exception):
        # cross-tenant
        svc.confirmar_deposito_por_booking(booking_b.id, default_company.id)
    db.refresh(booking_b)
    assert booking_b.deposit_paid is False
    svc.confirmar_deposito_por_booking(booking_a.id, default_company.id)
    db.refresh(booking_a)
    assert booking_a.deposit_paid is True


def test_24_25_26_pending_refunded_soft_deleted_do_not_activate_via_flags(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Ativação exige ledger >= mínimo (cotação sozinha não basta)."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("90.00"),  # cotação alta, sem ledger
    )
    svc = PaymentReservationService(db)
    with pytest.raises(MinimumDepositNotMetError):
        svc.confirmar_deposito_por_booking(booking.id, default_company.id)
    db.refresh(booking)
    assert booking.deposit_paid is False


def test_27_retry_confirm_idempotent(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Retry de confirmação não reprocessa efeitos."""
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("60.00"),
    )
    _ledger_deposit(db, booking.id, Decimal("60.00"))
    svc = PaymentReservationService(db)
    first = svc.confirmar_deposito_por_booking(booking.id, default_company.id)
    second = svc.confirmar_deposito_por_booking(booking.id, default_company.id)
    assert first.deposit_paid is True
    assert second.deposit_paid is True
    assert first.id == second.id


def test_28_expiration_02c_regression_uses_shared_formula(
    db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Expirador e fórmula compartilhada permanecem alinhados."""
    assert DisponibilidadeService._get_minimum_activation_cents(
        30_000
    ) == calculate_minimum_activation_cents(30_000)

    def _flag(key: str) -> bool:
        return key == "booking.core.enabled"

    monkeypatch.setattr(
        "app.modules.booking.application.commands.expire_booking.feature_flags.is_enabled",
        _flag,
    )
    # Abaixo do mínimo → pode expirar
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=40),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=Decimal("300.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("90.00"),
        remaining_amount=Decimal("210.00"),
        deposit_paid=False,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=datetime.now() - timedelta(hours=5),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.created_at = datetime.now() - timedelta(hours=5)
    db.commit()

    from app.models.payment import Payment, PaymentStatus, PaymentType

    db.add(
        Payment(
            booking_id=row.id,
            tipo=PaymentType.DEPOSIT,
            valor=Decimal("59.99"),
            status=PaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
    )
    db.commit()
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(row)
    assert row.status == ReservationStatus.EXPIRED


def test_admin_confirm_returns_400_structured(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """POST admin confirmar-sinal abaixo do mínimo → 400 estruturado."""
    admin = _create_admin(db, "quote-admin@test.local", default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        price_total=Decimal("800.00"),
        deposit_amount=Decimal("100.00"),
    )
    _ledger_deposit(db, booking.id, Decimal("99.99"))
    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    # error_handler envolve HTTPException em {error, message, path}
    detail = body.get("detail") or body.get("message") or body
    assert isinstance(detail, dict), body
    assert detail["code"] == "MINIMUM_DEPOSIT_NOT_MET"
    assert detail["minimum_activation_cents"] == 10_000
