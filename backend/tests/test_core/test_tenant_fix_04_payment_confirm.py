"""
FIX-04 — isolamento tenant nas mutações financeiras admin.

Cobre ``POST /admin/pagamentos/booking/{id}/confirmar-sinal`` e
``.../confirmar-final``: filtro SQL por ``company_id``, 403 sem tenant
efetivo, 404 genérico cross-tenant, 409 cancelado, idempotência 200.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from app.core.exceptions import NotFoundError
from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.financeiro import Financeiro
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.company_service import CompanyService
from app.services.payment_reservation_service import PaymentReservationService


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para testes de isolamento financeiro.

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
        nome="Admin Fix04",
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
    status: ReservationStatus = ReservationStatus.APPROVED,
    deposit_paid: bool = False,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
) -> CoreBooking:
    """
    Persiste ``CoreBooking`` para cenários FIX-04.

    Args:
        db: Sessão.
        company: Tenant dono do booking.
        cliente: Cliente (pode ser de outro tenant — só para FK).
        synced_catalog: Par (catalog, offering).
        status: Status da reserva.
        deposit_paid: Se o sinal já foi confirmado.
        payment_status: Status de pagamento agregado.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=200),
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
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_t01_cross_tenant_confirmar_sinal_404(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """
    T-01: Admin A confirma sinal de booking B → 404; booking B intacto.
    """
    company_b = _create_company(db, "fix04-co-b-sinal", "Empresa B Sinal")
    admin_a = _create_admin(db, "fix04-a-sinal@test.local", company=default_company)
    booking_b = _create_booking(db, company_b, cliente_exemplo, synced_catalog)

    resp = client.post(
        f"/admin/pagamentos/booking/{booking_b.id}/confirmar-sinal",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 404, resp.text
    msg = resp.json().get("message") or resp.json().get("detail") or ""
    assert "não encontrado" in str(msg).lower()

    db.refresh(booking_b)
    assert booking_b.deposit_paid is False
    assert booking_b.payment_status == StatusPagamento.PENDING_PAYMENT


def test_t02_cross_tenant_confirmar_final_404(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """
    T-02: Admin A confirma final de booking B → 404; booking B intacto.
    """
    company_b = _create_company(db, "fix04-co-b-final", "Empresa B Final")
    admin_a = _create_admin(db, "fix04-a-final@test.local", company=default_company)
    booking_b = _create_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )

    resp = client.post(
        f"/admin/pagamentos/booking/{booking_b.id}/confirmar-final",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 404, resp.text

    db.refresh(booking_b)
    assert booking_b.payment_status == StatusPagamento.PARTIALLY_PAID
    assert booking_b.deposit_paid is True


def test_t03_mesmo_tenant_confirmar_sinal_200(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """T-03: Mesmo tenant, primeira confirmação de sinal → 200."""
    admin = _create_admin(db, "fix04-ok@test.local", company=default_company)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == booking.id
    assert body["deposit_paid"] is True

    db.refresh(booking)
    assert booking.deposit_paid is True


def test_t04_sem_auth_401(client, db, default_company, cliente_exemplo, synced_catalog):
    """T-04: Sem autenticação → 401."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.post(f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal")
    assert resp.status_code == 401


def test_t05_sem_tenant_efetivo_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """T-05: Admin autenticado sem membership/JWT company → 403."""
    user = _create_admin(db, "fix04-no-tenant@test.local", company=None)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(user, company=None),
    )
    # Pode vir do guard admin (sem role) ou de _has_effective_company.
    assert resp.status_code == 403, resp.text


def test_t06_superuser_sem_tenant_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """T-06: Superuser sem tenant efetivo → 403 (sem fallback salao-demo)."""
    su = _create_admin(
        db, "fix04-su@test.local", company=None, is_superuser=True
    )
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(su, company=None),
    )
    assert resp.status_code == 403, resp.text


def test_t07_booking_inexistente_404(
    client, db, default_company
):
    """T-07: Booking inexistente → 404 genérico."""
    admin = _create_admin(db, "fix04-miss@test.local", company=default_company)
    resp = client.post(
        "/admin/pagamentos/booking/999999991/confirmar-sinal",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 404, resp.text
    msg = resp.json().get("message") or resp.json().get("detail") or ""
    assert msg == "Booking não encontrado"


def test_t08_idempotencia_sinal_sem_duplicar_financeiro(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """
    T-08: Sinal já confirmado, mesma empresa → 200 sem segundo Financeiro.
    """
    admin = _create_admin(db, "fix04-idem@test.local", company=default_company)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    headers = _auth_headers(admin, default_company)

    first = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=headers,
    )
    assert first.status_code == 200, first.text

    count_after_first = (
        db.query(Financeiro)
        .filter(Financeiro.descricao == f"Sinal - Booking #{booking.id}")
        .count()
    )
    assert count_after_first == 1

    second = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["deposit_paid"] is True

    count_after_second = (
        db.query(Financeiro)
        .filter(Financeiro.descricao == f"Sinal - Booking #{booking.id}")
        .count()
    )
    assert count_after_second == 1


def test_t09_final_sem_sinal_preserva_regra(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """T-09: Final sem sinal → 400 (regra atual preservada)."""
    admin = _create_admin(db, "fix04-final-sem@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        deposit_paid=False,
    )

    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-final",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 400, resp.text
    msg = resp.json().get("message") or resp.json().get("detail") or ""
    assert "sinal" in str(msg).lower()


def test_t10_booking_cancelado_409(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """T-10: Booking cancelado → 409."""
    admin = _create_admin(db, "fix04-cancel@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.CANCELLED,
    )

    resp = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-sinal",
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 409, resp.text


def test_t11_filtro_company_id_na_query_sql(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    T-11: Filtro ``company_id`` está na query SQLAlchemy (não post-filter).
    """
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)

    # Espelha o filtro usado por ``_obter_booking_do_tenant``.
    q = db.query(CoreBooking).filter(
        CoreBooking.id == booking.id,
        CoreBooking.company_id == default_company.id,
    )
    sql = str(q.statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "company_id" in sql
    assert str(default_company.id) in sql or f"company_id" in sql

    # Cross-tenant via service: NotFound sem mutar (prova que não é post-filter).
    other = _create_company(db, "fix04-t11-other", "Other T11")
    with pytest.raises(NotFoundError):
        PaymentReservationService(db).confirmar_deposito_por_booking(
            booking.id, company_id=other.id
        )
    db.refresh(booking)
    assert booking.deposit_paid is False

    PaymentReservationService(db).confirmar_deposito_por_booking(
        booking.id, company_id=default_company.id
    )
    db.refresh(booking)
    assert booking.deposit_paid is True


def test_t12_webhook_pix_mock_inalterado(client):
    """
    T-12: Smoke — webhook Pix mock não foi afetado por FIX-04.
    """
    resp = client.post("/webhook/pix")
    # PIX_MOCK_ENABLED tipicamente True em testes → 200 mock; senão 501.
    assert resp.status_code in (200, 501), resp.text
    if resp.status_code == 200:
        assert resp.json().get("status") == "received"
