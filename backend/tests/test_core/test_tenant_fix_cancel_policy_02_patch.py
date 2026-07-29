"""
FIX-CANCEL-POLICY-02 — janela configurável no ``PATCH /admin/agenda/{id}/status``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.admin_service import AdminService
from app.services.company_service import CompanyService


class _FixedClock:
    """
    Clock injetável com instante fixo para testes HTTP/service.

    Args:
        instant: Datetime retornado por ``now_utc``.
    """

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now_utc(self) -> datetime:
        """
        Retorna o instante configurado.

        Returns:
            Datetime do clock.
        """
        return self._instant


def _create_company(db, slug: str, nome: str | None = None) -> Company:
    """
    Cria empresa auxiliar para testes FIX-CANCEL-POLICY-02.

    Args:
        db: Sessão SQLAlchemy.
        slug: Slug único.
        nome: Nome comercial opcional.

    Returns:
        Company persistida.
    """
    company = Company(
        nome=nome or slug,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _create_admin(
    db,
    email: str,
    *,
    company: Company | None = None,
    is_superuser: bool = False,
) -> User:
    """
    Cria admin opcionalmente vinculado a uma empresa.

    Args:
        db: Sessão.
        email: E-mail único.
        company: Tenant para membership OWNER, se houver.
        is_superuser: Flag de superusuário.

    Returns:
        User persistido.
    """
    user = User(
        email=email,
        nome="Admin CancelPolicy02",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if company is not None:
        CompanyService(db).assign_user(user, company, CompanyRole.OWNER)
    return user


def _auth_headers(user: User, company: Company | None = None) -> dict:
    """
    Monta Authorization Bearer.

    Args:
        user: Usuário.
        company: Se informado, inclui ``company_id`` e role no JWT.

    Returns:
        Headers HTTP.
    """
    data = {"sub": str(user.id), "email": user.email}
    if company is not None:
        data["company_id"] = company.id
        data["role"] = "owner"
    token = create_access_token(data=data)
    return {"Authorization": f"Bearer {token}"}


def _upsert_cancel_hours(db, company_id: int, hours: int) -> None:
    """
    Grava override de ``approved_min_hours_before`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        hours: Valor N.
    """
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == company_id)
        .first()
    )
    payload = {"cancellation": {"approved_min_hours_before": hours}}
    now = datetime.utcnow()
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


def _create_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    status: ReservationStatus = ReservationStatus.CONFIRMADO,
    scheduled_at: datetime | None = None,
    deposit_paid: bool = False,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
    deleted_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste ``CoreBooking`` para cenários FIX-CANCEL-POLICY-02.

    Args:
        db: Sessão.
        company: Tenant dono.
        cliente: Cliente (FK).
        synced_catalog: Par (catalog, offering).
        status: Status da reserva.
        scheduled_at: Início vigente do slot (UTC/naive).
        deposit_paid: Sinal confirmado.
        payment_status: Status de pagamento agregado.
        deleted_at: Soft-delete opcional.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at or (datetime.now(timezone.utc) + timedelta(days=30)),
        status=status,
        payment_status=payment_status,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=deposit_paid,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        deleted_at=deleted_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _patch_status(client, booking_id: int, status: str, headers: dict):
    """
    Chama ``PATCH /admin/agenda/{id}/status``.

    Args:
        client: TestClient.
        booking_id: ID do booking.
        status: Novo status.
        headers: Authorization.

    Returns:
        Response HTTP.
    """
    return client.patch(
        f"/admin/agenda/{booking_id}/status",
        json={"status": status},
        headers=headers,
    )


def _patch_cancel_with_clock(
    monkeypatch,
    client,
    booking_id: int,
    headers: dict,
    now: datetime,
):
    """
    PATCH cancelado com clock controlado (SystemClockAdapter monkeypatched).

    Args:
        monkeypatch: Fixture pytest.
        client: TestClient.
        booking_id: ID do booking.
        headers: Authorization.
        now: Instante UTC do clock.

    Returns:
        Response HTTP.
    """
    fixed = _FixedClock(now)

    class _PatchedClock:
        """Clock de teste substituindo SystemClockAdapter no admin_service."""

        def now_utc(self) -> datetime:
            """
            Retorna o instante fixo do teste.

            Returns:
                Datetime configurado.
            """
            return fixed.now_utc()

    monkeypatch.setattr(
        "app.services.admin_service.SystemClockAdapter",
        _PatchedClock,
    )
    return _patch_status(client, booking_id, "cancelado", headers)


# ---------------------------------------------------------------------------
# Janela configurável
# ---------------------------------------------------------------------------


def test_01_approved_cancel_antes_da_janela_200(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """approved → cancelled antes da janela → 200."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 9, 14, 0, tzinfo=timezone.utc)  # 25h antes
    admin = _create_admin(db, "cp02-01@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONFIRMADO,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO


def test_02_approved_cancel_no_limite_exato_200(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """approved → cancelled exatamente no limite (N=24) → 200."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 9, 15, 0, tzinfo=timezone.utc)  # exatamente 24h
    admin = _create_admin(db, "cp02-02@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.APPROVED,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 200, resp.text


def test_03_approved_cancel_um_segundo_apos_limite_409(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """approved → cancelled 1s após o limite → 409 sem mutação."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 9, 15, 0, 1, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-03@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONFIRMADO,
        scheduled_at=start,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        deposit_paid=True,
    )
    prev_status = booking.status
    prev_payment = booking.payment_status
    prev_deleted = booking.deleted_at

    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 409, resp.text
    assert "cancel_policy_violation" in resp.text

    db.refresh(booking)
    assert booking.status == prev_status
    assert booking.payment_status == prev_payment
    assert booking.deleted_at == prev_deleted


def test_04_05_override_tenant_a_nao_usa_config_b(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Override N=48 do tenant A é respeitado; B com default 24 não vaza."""
    company_b = _create_company(db, "cp02-co-b")
    _upsert_cancel_hours(db, default_company.id, 48)

    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    # 36h antes: bloqueado para A (48h); permitido se usasse default 24
    now = datetime(2026, 8, 9, 3, 0, tzinfo=timezone.utc)

    admin_a = _create_admin(db, "cp02-04a@test.local", company=default_company)
    booking_a = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_a = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_a.id,
        _auth_headers(admin_a, default_company),
        now,
    )
    assert resp_a.status_code == 409, resp_a.text

    admin_b = _create_admin(db, "cp02-04b@test.local", company=company_b)
    booking_b = _create_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_b = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_b.id,
        _auth_headers(admin_b, company_b),
        now,
    )
    assert resp_b.status_code == 200, resp_b.text


def test_06_default_24h_sem_override(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Sem override, default 24h bloqueia 23h antes."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 9, 16, 0, tzinfo=timezone.utc)  # 23h
    admin = _create_admin(db, "cp02-06@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 409, resp.text


def test_07_08_n0_ate_inicio_e_apos(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """N=0: no início → 200; 1s após início → 409."""
    _upsert_cancel_hours(db, default_company.id, 0)
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-07@test.local", company=default_company)

    booking_ok = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_ok = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_ok.id,
        _auth_headers(admin, default_company),
        start,
    )
    assert resp_ok.status_code == 200, resp_ok.text

    booking_late = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_late = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_late.id,
        _auth_headers(admin, default_company),
        start + timedelta(seconds=1),
    )
    assert resp_late.status_code == 409, resp_late.text


def test_09_10_n1_boundary(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """N=1: exatamente 1h antes → 200; após → 409."""
    _upsert_cancel_hours(db, default_company.id, 1)
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-09@test.local", company=default_company)

    booking_ok = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_ok = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_ok.id,
        _auth_headers(admin, default_company),
        start - timedelta(hours=1),
    )
    assert resp_ok.status_code == 200, resp_ok.text

    booking_late = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp_late = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_late.id,
        _auth_headers(admin, default_company),
        start - timedelta(hours=1) + timedelta(seconds=1),
    )
    assert resp_late.status_code == 409, resp_late.text


def test_11_remarcado_usa_starts_at_vigente(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Booking remarcado usa ``scheduled_at`` vigente na avaliação."""
    old_start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    new_start = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    # Em relação ao old_start estaria fora; em relação ao new_start está ok.
    now = datetime(2026, 8, 19, 14, 0, tzinfo=timezone.utc)

    admin = _create_admin(db, "cp02-11@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=old_start,
    )
    booking.scheduled_at = new_start
    db.commit()
    db.refresh(booking)

    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 200, resp.text


def test_12_clock_injetavel_no_service(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Service usa o clock injetado (não o relógio da máquina)."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    # Agora "falso" dentro da janela
    AdminService(db).atualizar_status_agendamento(
        booking.id,
        ReservationStatus.CANCELADO,
        company_id=default_company.id,
        clock=_FixedClock(datetime(2026, 8, 9, 10, 0, tzinfo=timezone.utc)),
    )
    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO


# ---------------------------------------------------------------------------
# Estados
# ---------------------------------------------------------------------------


def test_13_pending_cancel_nao_aplica_janela(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """pending → cancelled não aplica janela (mesmo 1h antes do início)."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-13@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.PENDENTE,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO


def test_14_completed_cancel_bloqueado(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """completed → cancelled fora da matriz → 400 (contrato FIX-02b-write)."""
    start = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-14@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONCLUIDO,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 400, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CONCLUIDO


def test_15_expired_cancel_409(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """expired → cancelled bloqueado por proteção financeira → 409."""
    admin = _create_admin(db, "cp02-15@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.EXPIRED,
        deleted_at=datetime.utcnow(),
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 409, resp.text


def test_16_no_show_cancel_bloqueado(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """no_show → cancelled fora da matriz → 400."""
    admin = _create_admin(db, "cp02-16@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.NO_SHOW,
        scheduled_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 400, resp.text


def test_17_fsm_invalida_400(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Estado não permitido pela FSM → 400 (contrato atual)."""
    admin = _create_admin(db, "cp02-17@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONCLUIDO,
    )
    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 400, resp.text


def test_18_idempotencia_cancelado(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """cancelled → cancelled: 200 sem reavaliar janela nem alterar campos."""
    deleted_at = datetime.utcnow() - timedelta(hours=2)
    admin = _create_admin(db, "cp02-18@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CANCELADO,
        payment_status=StatusPagamento.CANCELLED,
        deleted_at=deleted_at,
        scheduled_at=datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc),
    )
    # Clock "tarde" — se reavaliasse janela, falharia; idempotência evita.
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 10, 14, 59, tzinfo=timezone.utc),
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO
    assert booking.payment_status == StatusPagamento.CANCELLED
    assert booking.deleted_at == deleted_at


def test_19_reabertura_permanece_bloqueada(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Tentativa de reabertura cancelled → approved permanece 409."""
    admin = _create_admin(db, "cp02-19@test.local", company=default_company)
    deleted_at = datetime.utcnow()
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CANCELADO,
        payment_status=StatusPagamento.CANCELLED,
        deleted_at=deleted_at,
    )
    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# Isolamento
# ---------------------------------------------------------------------------


def test_20_admin_a_cancela_booking_a_dentro_janela(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Admin A cancela booking A dentro da janela → 200."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-20@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 200, resp.text


def test_21_admin_a_booking_b_404(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Admin A tenta cancelar booking B → 404."""
    company_b = _create_company(db, "cp02-iso-b")
    admin_a = _create_admin(db, "cp02-21@test.local", company=default_company)
    booking_b = _create_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc),
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_b.id,
        _auth_headers(admin_a, default_company),
        datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 404, resp.text
    db.refresh(booking_b)
    assert booking_b.status == ReservationStatus.CONFIRMADO


def test_22_admin_sem_tenant_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Admin sem tenant efetivo → 403."""
    admin = _create_admin(db, "cp02-22@test.local", company=None, is_superuser=False)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = _patch_status(client, booking.id, "cancelado", _auth_headers(admin))
    assert resp.status_code == 403, resp.text


def test_23_superuser_sem_tenant_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Superuser sem tenant efetivo → 403."""
    admin = _create_admin(db, "cp02-23@test.local", company=None, is_superuser=True)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = _patch_status(client, booking.id, "cancelado", _auth_headers(admin))
    assert resp.status_code == 403, resp.text


def test_24_sem_bearer_401(client, db, default_company, cliente_exemplo, synced_catalog):
    """Sem Bearer → 401."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.patch(
        f"/admin/agenda/{booking.id}/status",
        json={"status": "cancelado"},
    )
    assert resp.status_code == 401, resp.text


def test_25_booking_inexistente_404(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Booking inexistente → 404."""
    admin = _create_admin(db, "cp02-25@test.local", company=default_company)
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        999999991,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 404, resp.text


def test_26_soft_deleted_contrato_02b(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """
    Soft-deleted cancelado: contrato FIX-02b-write (carregado; reabertura 409).

    Não há 404 silencioso — a proteção financeira permanece explícita.
    """
    admin = _create_admin(db, "cp02-26@test.local", company=default_company)
    deleted_at = datetime.utcnow()
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CANCELADO,
        payment_status=StatusPagamento.CANCELLED,
        deleted_at=deleted_at,
    )
    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 409, resp.text


def test_27_28_politica_tenant_b_nunca_para_a(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Política do tenant B (N=72) não é usada para booking de A (default 24)."""
    company_b = _create_company(db, "cp02-pol-b")
    _upsert_cancel_hours(db, company_b.id, 72)

    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    # 36h: ok para default 24; bloqueado se vazasse N=72
    now = datetime(2026, 8, 9, 3, 0, tzinfo=timezone.utc)

    admin_a = _create_admin(db, "cp02-27@test.local", company=default_company)
    booking_a = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking_a.id,
        _auth_headers(admin_a, default_company),
        now,
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Atomicidade e financeiro
# ---------------------------------------------------------------------------


def test_29_32_fora_janela_sem_efeitos_parciais(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Fora da janela: status, payment_status e deleted_at intactos."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 8, 9, 15, 0, 1, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-29@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        deposit_paid=True,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        now,
    )
    assert resp.status_code == 409, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CONFIRMADO
    assert booking.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking.deleted_at is None


def test_33_34_cancel_permitido_preserva_efeitos(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Cancelamento permitido: payment_status=CANCELLED e deleted_at setados."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-33@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        deposit_paid=True,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.payment_status == StatusPagamento.CANCELLED
    assert booking.deleted_at is not None


def test_35_confirmacao_financeira_bloqueada_apos_cancel(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Após cancelamento, confirmação de sinal permanece bloqueada (409)."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-35@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        deposit_paid=False,
    )
    resp = _patch_cancel_with_clock(
        monkeypatch,
        client,
        booking.id,
        _auth_headers(admin, default_company),
        datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
    )
    assert resp.status_code == 200, resp.text

    pay = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(admin, default_company),
    )
    assert pay.status_code == 409, pay.text
    db.refresh(booking)
    assert booking.payment_status == StatusPagamento.CANCELLED
    assert booking.deposit_paid is False


def test_36_retry_nao_duplica_efeitos(
    client, db, default_company, cliente_exemplo, synced_catalog, monkeypatch
):
    """Retry de cancelamento: idempotente; deleted_at/payment não duplicam efeitos."""
    start = datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc)
    admin = _create_admin(db, "cp02-36@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        scheduled_at=start,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        deposit_paid=True,
    )
    headers = _auth_headers(admin, default_company)
    now = datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)

    resp1 = _patch_cancel_with_clock(monkeypatch, client, booking.id, headers, now)
    assert resp1.status_code == 200, resp1.text
    db.refresh(booking)
    deleted_first = booking.deleted_at
    payment_first = booking.payment_status

    resp2 = _patch_cancel_with_clock(monkeypatch, client, booking.id, headers, now)
    assert resp2.status_code == 200, resp2.text
    db.refresh(booking)
    assert booking.deleted_at == deleted_first
    assert booking.payment_status == payment_first == StatusPagamento.CANCELLED
