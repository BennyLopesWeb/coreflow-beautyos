"""
FIX-02b-write — isolamento e FSM do ``PATCH /admin/agenda/{id}/status``.
"""
from __future__ import annotations

from datetime import datetime, timedelta
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


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para testes FIX-02b-write.

    Args:
        db: Sessão SQLAlchemy.
        slug: Slug único.
        nome: Nome comercial.

    Returns:
        Company persistida.
    """
    company = Company(
        nome=nome,
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
        nome="Admin Fix02b",
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


def _create_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    status: ReservationStatus = ReservationStatus.PENDENTE,
    deposit_paid: bool = False,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
    deleted_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste ``CoreBooking`` para cenários FIX-02b-write.

    Args:
        db: Sessão.
        company: Tenant dono.
        cliente: Cliente (FK).
        synced_catalog: Par (catalog, offering).
        status: Status da reserva.
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
        scheduled_at=datetime.now() + timedelta(days=30),
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


def test_cross_tenant_patch_status_404(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Admin A não altera booking da empresa B (404; booking intacto)."""
    company_b = _create_company(db, "fix02b-co-b", "Empresa B Fix02b")
    admin_a = _create_admin(db, "fix02b-a@test.local", company=default_company)
    booking_b = _create_booking(
        db, company_b, cliente_exemplo, synced_catalog, status=ReservationStatus.PENDENTE
    )

    resp = _patch_status(
        client, booking_b.id, "confirmado", _auth_headers(admin_a, default_company)
    )
    assert resp.status_code == 404, resp.text

    db.refresh(booking_b)
    assert booking_b.status == ReservationStatus.PENDENTE
    assert booking_b.company_id == company_b.id


def test_sem_tenant_efetivo_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Superuser/admin sem tenant efetivo recebe 403."""
    admin = _create_admin(db, "fix02b-orphan@test.local", company=None, is_superuser=True)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    resp = _patch_status(client, booking.id, "confirmado", _auth_headers(admin))
    assert resp.status_code == 403, resp.text

    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDENTE


def test_sem_bearer_401(client, db, default_company, cliente_exemplo, synced_catalog):
    """Sem Authorization → 401."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.patch(
        f"/admin/agenda/{booking.id}/status",
        json={"status": "confirmado"},
    )
    assert resp.status_code == 401, resp.text


def test_mesmo_tenant_pendente_para_confirmado(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Transição FE pendente → confirmado permitida no mesmo tenant."""
    admin = _create_admin(db, "fix02b-ok@test.local", company=default_company)
    booking = _create_booking(
        db, default_company, cliente_exemplo, synced_catalog, status=ReservationStatus.PENDENTE
    )

    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CONFIRMADO


def test_confirmado_para_cancelado_preserva_financeiro(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Cancelamento via PATCH seta payment_status e soft-delete."""
    admin = _create_admin(db, "fix02b-cancel@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONFIRMADO,
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )

    resp = _patch_status(
        client, booking.id, "cancelado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO
    assert booking.payment_status == StatusPagamento.CANCELLED
    assert booking.deleted_at is not None


def test_bloqueia_reabertura_cancelado(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Cancelado não pode voltar para confirmado (409); campos financeiros intactos."""
    admin = _create_admin(db, "fix02b-reopen@test.local", company=default_company)
    deleted_at = datetime.utcnow() - timedelta(hours=1)
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

    db.refresh(booking)
    assert booking.status == ReservationStatus.CANCELADO
    assert booking.payment_status == StatusPagamento.CANCELLED
    assert booking.deleted_at == deleted_at


def test_bloqueia_reabertura_expired(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Expired não pode ser reaberto para pendente (409)."""
    admin = _create_admin(db, "fix02b-exp@test.local", company=default_company)
    deleted_at = datetime.utcnow()
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.EXPIRED,
        deleted_at=deleted_at,
    )

    resp = _patch_status(
        client, booking.id, "pendente", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 409, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.deleted_at == deleted_at


def test_transicao_invalida_400(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Concluído → confirmado fora da matriz → 400."""
    admin = _create_admin(db, "fix02b-bad-tr@test.local", company=default_company)
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
    db.refresh(booking)
    assert booking.status == ReservationStatus.CONCLUIDO


def test_idempotente_mesmo_lifecycle(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Mesmo lifecycle (confirmado → approved) retorna 200 sem erro."""
    admin = _create_admin(db, "fix02b-idem@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CONFIRMADO,
    )

    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 200, resp.text
    db.refresh(booking)
    assert booking.status == ReservationStatus.CONFIRMADO


def test_service_exige_company_id(db, default_company, cliente_exemplo, synced_catalog):
    """Service rejeita company_id ausente (sem inferência)."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    with pytest.raises(ValueError, match="company_id"):
        AdminService(db).atualizar_status_agendamento(
            booking.id, ReservationStatus.CONFIRMADO, company_id=None  # type: ignore[arg-type]
        )


def test_service_isolamento_sql(db, default_company, cliente_exemplo, synced_catalog):
    """Query do service não encontra booking de outro tenant."""
    from app.core.exceptions import NotFoundError

    company_b = _create_company(db, "fix02b-svc-b", "Svc B")
    booking_b = _create_booking(db, company_b, cliente_exemplo, synced_catalog)

    with pytest.raises(NotFoundError):
        AdminService(db).atualizar_status_agendamento(
            booking_b.id,
            ReservationStatus.CONFIRMADO,
            company_id=default_company.id,
        )


def test_policy_manual_status_disabled_409(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Override com manual_status.enabled=false → 409."""
    now = datetime.utcnow()
    db.add(
        BookingPolicyConfig(
            company_id=default_company.id,
            policy_json={"manual_status": {"enabled": False}},
            version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    admin = _create_admin(db, "fix02b-pol@test.local", company=default_company)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    resp = _patch_status(
        client, booking.id, "confirmado", _auth_headers(admin, default_company)
    )
    assert resp.status_code == 409, resp.text
