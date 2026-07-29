"""
FIX-02a — isolamento multi-tenant de ``GET /admin/dashboard``.

Garante agregações SQL por ``company_id`` (Cliente, CoreBooking, Fila,
Financeiro), 401 sem Bearer e 403 sem tenant efetivo.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus
from app.models.cliente import Cliente
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.fila import Fila, StatusFila
from app.models.financeiro import Financeiro, TipoMovimento
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.company_service import CompanyService


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para isolamento do dashboard.

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
        nome="Admin Fix02a",
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


def _create_cliente(db, company_id: int, nome: str, telefone: str) -> Cliente:
    """
    Persiste cliente do tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        nome: Nome.
        telefone: Telefone único.

    Returns:
        Cliente persistido.
    """
    cliente = Cliente(
        nome=nome,
        telefone=telefone,
        email=f"{telefone}@fix02a.local",
        company_id=company_id,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def _create_booking(
    db,
    company_id: int,
    customer_id: int,
    catalog_id: int,
    offering_id: int,
    *,
    status: ReservationStatus = ReservationStatus.PENDING_PAYMENT,
    deposit_paid: bool = False,
    scheduled_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste booking mínimo para métricas do dashboard.

    Args:
        db: Sessão.
        company_id: Tenant.
        customer_id: Cliente.
        catalog_id: Catálogo.
        offering_id: Offering.
        status: Status da reserva.
        deposit_paid: Sinal confirmado.
        scheduled_at: Horário; default amanhã.

    Returns:
        CoreBooking persistido.
    """
    booking = CoreBooking(
        company_id=company_id,
        customer_id=customer_id,
        catalog_id=catalog_id,
        offering_id=offering_id,
        scheduled_at=scheduled_at or (datetime.now() + timedelta(days=1)),
        status=status,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=deposit_paid,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def _create_fila(
    db,
    company_id: int,
    cliente_id: int,
    tranca_id: int,
    service_image_id: int,
    posicao: int,
) -> Fila:
    """
    Persiste item de fila ativa do dia para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        cliente_id: Cliente.
        tranca_id: Trança.
        service_image_id: Imagem de serviço.
        posicao: Posição na fila.

    Returns:
        Fila persistida.
    """
    item = Fila(
        company_id=company_id,
        cliente_id=cliente_id,
        tranca_id=tranca_id,
        service_image_id=service_image_id,
        data=date.today(),
        horario_desejado=time(10, 0),
        posicao=posicao,
        status=StatusFila.WAITING,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _create_financeiro(
    db,
    company_id: int,
    tipo: TipoMovimento,
    valor: Decimal,
    descricao: str,
) -> Financeiro:
    """
    Persiste movimento financeiro do mês corrente no tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        tipo: Entrada ou saída.
        valor: Valor.
        descricao: Descrição única.

    Returns:
        Financeiro persistido.
    """
    mov = Financeiro(
        company_id=company_id,
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        data=datetime.now(),
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


def _seed_two_tenants(db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo):
    """
    Popula empresa A (default) e empresa B com contagens distintas.

    Args:
        db: Sessão.
        default_company: Empresa A.
        synced_catalog: Par (catalog, offering).
        tranca_exemplo: Trança seed.
        service_image_exemplo: Service image seed.

    Returns:
        Tupla ``(company_b, expected_a, expected_b)`` com dicts de métricas.
    """
    catalog, offering = synced_catalog
    company_b = _create_company(db, "fix02a-co-b", "Empresa B Fix02a")

    # --- Empresa A: 2 clientes, 2 bookings (1 pending, 1 approved+paid), 1 fila, fin ---
    ca1 = _create_cliente(db, default_company.id, "Cli A1", "11982000001")
    ca2 = _create_cliente(db, default_company.id, "Cli A2", "11982000002")
    _create_booking(
        db,
        default_company.id,
        ca1.id,
        catalog.id,
        offering.id,
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
    )
    _create_booking(
        db,
        default_company.id,
        ca2.id,
        catalog.id,
        offering.id,
        status=ReservationStatus.APPROVED,
        deposit_paid=True,
        scheduled_at=datetime.combine(date.today(), time(14, 0)),
    )
    _create_fila(
        db,
        default_company.id,
        ca1.id,
        tranca_exemplo.id,
        service_image_exemplo.id,
        posicao=1,
    )
    _create_financeiro(
        db,
        default_company.id,
        TipoMovimento.ENTRADA,
        Decimal("100.00"),
        "Entrada A Fix02a",
    )
    _create_financeiro(
        db,
        default_company.id,
        TipoMovimento.SAIDA,
        Decimal("20.00"),
        "Saida A Fix02a",
    )

    # --- Empresa B: 1 cliente, 1 booking pending, 2 fila, fin maior ---
    cb1 = _create_cliente(db, company_b.id, "Cli B1", "11982000011")
    _create_booking(
        db,
        company_b.id,
        cb1.id,
        catalog.id,
        offering.id,
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
    )
    _create_fila(
        db, company_b.id, cb1.id, tranca_exemplo.id, service_image_exemplo.id, 1
    )
    _create_fila(
        db, company_b.id, cb1.id, tranca_exemplo.id, service_image_exemplo.id, 2
    )
    _create_financeiro(
        db,
        company_b.id,
        TipoMovimento.ENTRADA,
        Decimal("500.00"),
        "Entrada B Fix02a",
    )
    _create_financeiro(
        db,
        company_b.id,
        TipoMovimento.SAIDA,
        Decimal("50.00"),
        "Saida B Fix02a",
    )

    expected_a = {
        "total_clientes": 2,
        "total_agendamentos": 2,
        "agendamentos_pendentes": 1,
        "aguardando_aprovacao": 0,
        "agendamentos_confirmados": 1,
        "agendamentos_hoje": 1,
        "fila_hoje": 1,
        "pagamentos_pendentes": 1,
        "pagamentos_confirmados": 1,
        "receita_mes": Decimal("100.00"),
        "saldo_mes": Decimal("80.00"),
    }
    expected_b = {
        "total_clientes": 1,
        "total_agendamentos": 1,
        "agendamentos_pendentes": 1,
        "aguardando_aprovacao": 0,
        "agendamentos_confirmados": 0,
        "agendamentos_hoje": 0,
        "fila_hoje": 2,
        "pagamentos_pendentes": 1,
        "pagamentos_confirmados": 0,
        "receita_mes": Decimal("500.00"),
        "saldo_mes": Decimal("450.00"),
    }
    return company_b, expected_a, expected_b


def _assert_dashboard(body: dict, expected: dict) -> None:
    """
    Compara payload do dashboard com métricas esperadas.

    Args:
        body: JSON da resposta HTTP.
        expected: Dict de contadores/valores.
    """
    for key, value in expected.items():
        if isinstance(value, Decimal):
            assert Decimal(str(body[key])) == value, f"{key}: {body[key]} != {value}"
        else:
            assert body[key] == value, f"{key}: {body[key]} != {value}"


@pytest.mark.unit
def test_dashboard_admin_a_isola_de_b(
    client, db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """Admin A recebe métricas somente da empresa A."""
    company_b, expected_a, expected_b = _seed_two_tenants(
        db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
    )
    admin_a = _create_admin(db, "fix02a-a@test.local", company=default_company)

    resp = client.get(
        "/admin/dashboard",
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_dashboard(body, expected_a)
    # Não é a soma global (A+B)
    assert body["total_clientes"] != expected_a["total_clientes"] + expected_b["total_clientes"]
    assert company_b.id != default_company.id


@pytest.mark.unit
def test_dashboard_admin_b_isola_de_a(
    client, db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """Admin B recebe métricas somente da empresa B (valores distintos de A)."""
    company_b, expected_a, expected_b = _seed_two_tenants(
        db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
    )
    admin_b = _create_admin(db, "fix02a-b@test.local", company=company_b)

    resp = client.get(
        "/admin/dashboard",
        headers=_auth_headers(admin_b, company_b),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_dashboard(body, expected_b)
    assert body["total_clientes"] != expected_a["total_clientes"]
    assert body["fila_hoje"] != expected_a["fila_hoje"]
    assert Decimal(str(body["receita_mes"])) != expected_a["receita_mes"]


@pytest.mark.unit
def test_dashboard_sem_auth_401(client):
    """Sem Bearer → 401."""
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 401


@pytest.mark.unit
def test_dashboard_sem_tenant_efetivo_403(
    client, db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """Autenticado sem membership/JWT company → 403 (sem dump)."""
    _seed_two_tenants(
        db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
    )
    user = _create_admin(db, "fix02a-no-tenant@test.local", company=None)

    resp = client.get(
        "/admin/dashboard",
        headers=_auth_headers(user, company=None),
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.unit
def test_dashboard_superuser_sem_tenant_403(
    client, db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """Superuser sem tenant efetivo → 403 (sem fallback salao-demo)."""
    _seed_two_tenants(
        db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
    )
    su = _create_admin(
        db, "fix02a-su@test.local", company=None, is_superuser=True
    )

    resp = client.get(
        "/admin/dashboard",
        headers=_auth_headers(su, company=None),
    )
    assert resp.status_code == 403, resp.text
    msg = resp.json().get("message") or resp.json().get("detail") or ""
    assert "Tenant" in str(msg)


@pytest.mark.unit
def test_dashboard_contadores_individuais_por_tenant(
    client, db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
):
    """
    Cada contador (clientes, bookings, fila, financeiro) reflete só o tenant.

    Dados de A e B coexistem no banco; asserts numéricos explícitos.
    """
    company_b, expected_a, expected_b = _seed_two_tenants(
        db, default_company, synced_catalog, tranca_exemplo, service_image_exemplo
    )
    admin_a = _create_admin(db, "fix02a-cnt-a@test.local", company=default_company)
    admin_b = _create_admin(db, "fix02a-cnt-b@test.local", company=company_b)

    resp_a = client.get(
        "/admin/dashboard",
        headers=_auth_headers(admin_a, default_company),
    )
    resp_b = client.get(
        "/admin/dashboard",
        headers=_auth_headers(admin_b, company_b),
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    a = resp_a.json()
    b = resp_b.json()

    # Clientes
    assert a["total_clientes"] == 2
    assert b["total_clientes"] == 1
    # Bookings
    assert a["total_agendamentos"] == 2
    assert b["total_agendamentos"] == 1
    assert a["agendamentos_confirmados"] == 1
    assert b["agendamentos_confirmados"] == 0
    assert a["agendamentos_hoje"] == 1
    assert b["agendamentos_hoje"] == 0
    assert a["pagamentos_confirmados"] == 1
    assert b["pagamentos_confirmados"] == 0
    # Fila
    assert a["fila_hoje"] == 1
    assert b["fila_hoje"] == 2
    # Financeiro
    assert Decimal(str(a["receita_mes"])) == Decimal("100.00")
    assert Decimal(str(b["receita_mes"])) == Decimal("500.00")
    assert Decimal(str(a["saldo_mes"])) == Decimal("80.00")
    assert Decimal(str(b["saldo_mes"])) == Decimal("450.00")

    _assert_dashboard(a, expected_a)
    _assert_dashboard(b, expected_b)
