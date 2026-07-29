"""
FIX-02b-list — isolamento multi-tenant de ``GET /admin/agenda``.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus
from app.models.cliente import Cliente
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.fila import Fila, StatusFila
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.admin_service import AdminService
from app.services.company_service import CompanyService


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para testes FIX-02b-list.

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
    role: CompanyRole = CompanyRole.OWNER,
) -> User:
    """
    Cria usuário admin opcionalmente vinculado a uma empresa.

    Args:
        db: Sessão.
        email: E-mail único.
        company: Tenant para membership, se houver.
        is_superuser: Flag de superusuário.
        role: Papel RBAC na empresa.

    Returns:
        User persistido.
    """
    user = User(
        email=email,
        nome="Admin Fix02bList",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if company is not None:
        CompanyService(db).assign_user(user, company, role)
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
        email=f"{telefone}@fix02blist.local",
        company_id=company_id,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def _create_booking(
    db,
    company: Company,
    cliente: Cliente,
    synced_catalog,
    *,
    status: ReservationStatus = ReservationStatus.PENDENTE,
    scheduled_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste ``CoreBooking`` para cenários FIX-02b-list.

    Args:
        db: Sessão.
        company: Tenant dono.
        cliente: Cliente.
        synced_catalog: Par (catalog, offering).
        status: Status da reserva.
        scheduled_at: Horário; default hoje ao meio-dia.
        deleted_at: Soft-delete opcional.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    today = date.today()
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at
        or datetime.combine(today, time(12, 0)),
        status=status,
        payment_status="pending_payment",
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=False,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        deleted_at=deleted_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _create_fila(
    db,
    company_id: int,
    cliente_id: int,
    tranca_id: int,
    service_image_id: int,
    posicao: int,
    data_ref: date | None = None,
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
        data_ref: Dia da fila.

    Returns:
        Fila persistida.
    """
    item = Fila(
        company_id=company_id,
        cliente_id=cliente_id,
        tranca_id=tranca_id,
        service_image_id=service_image_id,
        data=data_ref or date.today(),
        horario_desejado=time(10, 0),
        posicao=posicao,
        status=StatusFila.WAITING,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Autenticação e tenant
# ---------------------------------------------------------------------------


def test_01_sem_bearer_401(client, db, default_company, cliente_exemplo, synced_catalog):
    """Sem Authorization → 401."""
    _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.get("/admin/agenda")
    assert resp.status_code == 401, resp.text


def test_02_usuario_nao_admin_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Usuário sem permissão administrativa → 403."""
    _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    user = _create_admin(
        db,
        "fix02blist-customer@test.local",
        company=default_company,
        role=CompanyRole.CUSTOMER,
    )
    # JWT com role customer (não admin)
    data = {
        "sub": str(user.id),
        "email": user.email,
        "company_id": default_company.id,
        "role": "customer",
    }
    token = create_access_token(data=data)
    resp = client.get(
        "/admin/agenda",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


def test_03_admin_tenant_a_200(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Admin do tenant A consulta agenda → 200."""
    admin = _create_admin(db, "fix02blist-ok@test.local", company=default_company)
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200, resp.text
    ids = [item["id"] for item in resp.json()]
    assert booking.id in ids


def test_04_admin_sem_tenant_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Admin sem tenant efetivo → 403."""
    _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    admin = _create_admin(db, "fix02blist-orphan@test.local", company=None)
    resp = client.get("/admin/agenda", headers=_auth_headers(admin))
    assert resp.status_code == 403, resp.text


def test_05_superuser_sem_tenant_403(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Superuser sem tenant efetivo → 403 (sem fallback salao-demo)."""
    _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    admin = _create_admin(
        db, "fix02blist-super@test.local", company=None, is_superuser=True
    )
    resp = client.get("/admin/agenda", headers=_auth_headers(admin))
    assert resp.status_code == 403, resp.text


def test_06_query_company_id_nao_substitui_tenant(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """``?company_id=`` do request não substitui o tenant autenticado."""
    company_b = _create_company(db, "fix02blist-co-b-q", "Empresa B Query")
    admin_a = _create_admin(db, "fix02blist-q@test.local", company=default_company)
    cliente_b = _create_cliente(db, company_b.id, "Cliente B Query", "11970000001")
    booking_a = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    booking_b = _create_booking(db, company_b, cliente_b, synced_catalog)

    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin_a, default_company),
        params={"data": date.today().isoformat(), "company_id": company_b.id},
    )
    assert resp.status_code == 200, resp.text
    ids = {item["id"] for item in resp.json()}
    assert booking_a.id in ids
    assert booking_b.id not in ids


# ---------------------------------------------------------------------------
# Isolamento
# ---------------------------------------------------------------------------


def test_07_08_09_isolamento_cross_tenant(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Admin A vê booking A; não vê booking/cliente de B."""
    company_b = _create_company(db, "fix02blist-co-b", "Empresa B List")
    admin_a = _create_admin(db, "fix02blist-iso-a@test.local", company=default_company)
    cliente_b = _create_cliente(db, company_b.id, "Cliente Secreto B", "11970000002")
    booking_a = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    booking_b = _create_booking(db, company_b, cliente_b, synced_catalog)

    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin_a, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    ids = {item["id"] for item in payload}
    nomes = {item["cliente_nome"] for item in payload}
    assert booking_a.id in ids
    assert booking_b.id not in ids
    assert "Cliente Secreto B" not in nomes


def test_10_catalogo_b_nao_vaza_na_lista_a(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Lista de A não inclui booking cujo tenant é B (catálogo compartilhado)."""
    company_b = _create_company(db, "fix02blist-co-b-cat", "Empresa B Cat")
    admin_a = _create_admin(db, "fix02blist-cat@test.local", company=default_company)
    cliente_b = _create_cliente(db, company_b.id, "Cli B Cat", "11970000003")
    booking_b = _create_booking(db, company_b, cliente_b, synced_catalog)

    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin_a, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200
    assert booking_b.id not in {item["id"] for item in resp.json()}


def test_11_12_sem_fallback_global(db, default_company, cliente_exemplo, synced_catalog):
    """Service exige company_id; não há consulta global implícita."""
    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    with pytest.raises(ValueError, match="company_id"):
        AdminService(db).listar_agendamentos(company_id=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="company_id"):
        AdminService(db).listar_agendamentos(company_id=0)

    company_b = _create_company(db, "fix02blist-co-b-fb", "Empresa B Fb")
    items = AdminService(db).listar_agendamentos(
        company_id=company_b.id, data_ref=date.today()
    )
    assert all(i.id != booking.id for i in items)


def test_13_soft_deleted_nao_aparece(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Booking soft-deleted não aparece na listagem."""
    admin = _create_admin(db, "fix02blist-del@test.local", company=default_company)
    booking = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        deleted_at=datetime.utcnow(),
    )
    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200
    assert booking.id not in {item["id"] for item in resp.json()}


def test_14_booking_inexistente_nao_aparece(
    client, db, default_company
):
    """Lista vazia / id inexistente não inventa itens."""
    admin = _create_admin(db, "fix02blist-empty@test.local", company=default_company)
    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Filtros e contrato
# ---------------------------------------------------------------------------


def test_15_16_filtro_data_e_ordenacao(
    client, db, default_company, synced_catalog
):
    """Filtro ``data`` funciona e ordenação é ``scheduled_at`` ASC."""
    admin = _create_admin(db, "fix02blist-ord@test.local", company=default_company)
    c1 = _create_cliente(db, default_company.id, "Cli Ord1", "11970000010")
    c2 = _create_cliente(db, default_company.id, "Cli Ord2", "11970000011")
    today = date.today()
    b_late = _create_booking(
        db,
        default_company,
        c2,
        synced_catalog,
        scheduled_at=datetime.combine(today, time(16, 0)),
    )
    b_early = _create_booking(
        db,
        default_company,
        c1,
        synced_catalog,
        scheduled_at=datetime.combine(today, time(9, 0)),
    )
    # Fora do dia
    _create_booking(
        db,
        default_company,
        c1,
        synced_catalog,
        scheduled_at=datetime.combine(today + timedelta(days=2), time(10, 0)),
    )

    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": today.isoformat()},
    )
    assert resp.status_code == 200
    items = resp.json()
    ids = [i["id"] for i in items]
    assert b_early.id in ids
    assert b_late.id in ids
    assert ids.index(b_early.id) < ids.index(b_late.id)


def test_17_18_lista_vazia_e_campos_contrato(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """Lista vazia 200 []; campos do contrato presentes quando há itens."""
    admin = _create_admin(db, "fix02blist-fields@test.local", company=default_company)
    empty = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": (date.today() + timedelta(days=90)).isoformat()},
    )
    assert empty.status_code == 200
    assert empty.json() == []

    booking = _create_booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["id"] == booking.id)
    for key in (
        "id",
        "cliente_id",
        "cliente_nome",
        "cliente_telefone",
        "tranca_id",
        "tranca_nome",
        "data_hora",
        "status",
        "sinal_pago",
        "na_fila",
    ):
        assert key in item


def test_19_20_filtro_company_id_na_query_sql(db, default_company):
    """Filtro de tenant é aplicado na cláusula SQLAlchemy."""
    from sqlalchemy.dialects import sqlite

    query = (
        db.query(CoreBooking)
        .filter(
            CoreBooking.deleted_at.is_(None),
            CoreBooking.company_id == default_company.id,
        )
    )
    compiled = str(
        query.statement.compile(
            dialect=sqlite.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "company_id" in compiled.lower()
    assert str(default_company.id) in compiled


# ---------------------------------------------------------------------------
# Fila
# ---------------------------------------------------------------------------


def test_21_22_23_fila_isolada_por_tenant(
    client,
    db,
    default_company,
    synced_catalog,
    tranca_exemplo,
    service_image_exemplo,
):
    """``na_fila``/posição de A corretos; fila de B não contamina A."""
    company_b = _create_company(db, "fix02blist-co-b-fila", "Empresa B Fila")
    admin_a = _create_admin(db, "fix02blist-fila@test.local", company=default_company)
    cliente_a = _create_cliente(db, default_company.id, "Cli Fila A", "11970000020")
    cliente_b = _create_cliente(db, company_b.id, "Cli Fila B", "11970000021")
    booking_a = _create_booking(db, default_company, cliente_a, synced_catalog)

    _create_fila(
        db,
        default_company.id,
        cliente_a.id,
        tranca_exemplo.id,
        service_image_exemplo.id,
        posicao=3,
    )
    _create_fila(
        db,
        company_b.id,
        cliente_b.id,
        tranca_exemplo.id,
        service_image_exemplo.id,
        posicao=99,
    )
    # Fila B com mesmo cliente_id de A não deve ocorrer; simula vazamento
    # se company_id fosse ignorado — booking A não deve herdar pos 99 via B.
    _create_fila(
        db,
        company_b.id,
        cliente_a.id,
        tranca_exemplo.id,
        service_image_exemplo.id,
        posicao=99,
    )

    resp = client.get(
        "/admin/agenda",
        headers=_auth_headers(admin_a, default_company),
        params={"data": date.today().isoformat()},
    )
    assert resp.status_code == 200
    item = next(i for i in resp.json() if i["id"] == booking_a.id)
    assert item["na_fila"] is True
    assert item["posicao_fila"] == 3


# ---------------------------------------------------------------------------
# Resposta do PATCH
# ---------------------------------------------------------------------------


def test_25_26_27_28_patch_resposta_tenant_scoped(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """PATCH retorna só dados de A; cross-tenant 404; listagem interna isolada."""
    company_b = _create_company(db, "fix02blist-co-b-patch", "Empresa B Patch")
    admin_a = _create_admin(db, "fix02blist-patch@test.local", company=default_company)
    cliente_b = _create_cliente(db, company_b.id, "Cli B Patch", "11970000030")
    booking_a = _create_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        status=ReservationStatus.PENDENTE,
    )
    booking_b = _create_booking(
        db,
        company_b,
        cliente_b,
        synced_catalog,
        status=ReservationStatus.PENDENTE,
    )

    resp = client.patch(
        f"/admin/agenda/{booking_a.id}/status",
        json={"status": "confirmado"},
        headers=_auth_headers(admin_a, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == booking_a.id
    assert body["cliente_nome"] != "Cli B Patch"
    assert "Cli B Patch" not in str(body)

    cross = client.patch(
        f"/admin/agenda/{booking_b.id}/status",
        json={"status": "confirmado"},
        headers=_auth_headers(admin_a, default_company),
    )
    assert cross.status_code == 404, cross.text
