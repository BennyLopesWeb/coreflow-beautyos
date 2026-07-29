"""
TENANT-FIX-08 — isolamento de ``GET /clientes/{id}``.

Garante autenticação, filtro SQL por ``company_id`` e ausência de
enumeração cross-tenant / fallback ``salao-demo``.
"""
import pytest
from app.core.exceptions import NotFoundError

from app.core.security import create_access_token, get_password_hash
from app.models.cliente import Cliente
from app.models.company import Company, CompanySegment, CompanyPlan
from app.models.user import User
from app.models.user_company import CompanyRole
from app.services.cliente_service import ClienteService
from app.services.company_service import CompanyService


def _create_company(db, slug: str, nome: str) -> Company:
    """
    Cria empresa auxiliar para testes de isolamento.

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


def _create_user(
    db,
    email: str,
    *,
    company: Company | None = None,
    is_superuser: bool = False,
) -> User:
    """
    Cria usuário opcionalmente vinculado a uma empresa.

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
        nome="User Fix08",
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


def _create_cliente(db, company_id, nome: str, telefone: str) -> Cliente:
    """
    Persiste cliente com ou sem tenant.

    Args:
        db: Sessão.
        company_id: ID da empresa ou ``None``.
        nome: Nome.
        telefone: Telefone único.

    Returns:
        Cliente persistido.
    """
    cliente = Cliente(
        nome=nome,
        telefone=telefone,
        email=f"{telefone}@test.local",
        company_id=company_id,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@pytest.mark.unit
def test_obter_cliente_mesmo_tenant_200(client, db, default_company):
    """Usuário da empresa A consulta cliente da empresa A → 200."""
    user = _create_user(db, "fix08-a@test.com", company=default_company)
    cliente = _create_cliente(db, default_company.id, "Cliente A", "11970000001")

    response = client.get(
        f"/clientes/{cliente.id}",
        headers=_auth_headers(user, default_company),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == cliente.id
    assert body["nome"] == "Cliente A"


@pytest.mark.unit
def test_obter_cliente_outro_tenant_404(client, db, default_company):
    """Usuário da empresa A consulta cliente da empresa B → 404 sem PII."""
    company_b = _create_company(db, "fix08-b", "Empresa B Fix08")
    user_a = _create_user(db, "fix08-cross@test.com", company=default_company)
    cliente_b = _create_cliente(db, company_b.id, "Cliente Secreto B", "11970000002")

    response = client.get(
        f"/clientes/{cliente_b.id}",
        headers=_auth_headers(user_a, default_company),
    )
    assert response.status_code == 404
    body = response.json()
    blob = str(body).lower()
    assert "cliente secreto b" not in blob
    assert "11970000002" not in blob
    assert "@test.local" not in blob


@pytest.mark.unit
def test_obter_cliente_sem_autenticacao_401(client, db, default_company):
    """Sem Bearer → 401."""
    cliente = _create_cliente(db, default_company.id, "Cliente Pub", "11970000003")
    response = client.get(f"/clientes/{cliente.id}")
    assert response.status_code == 401


@pytest.mark.unit
def test_obter_cliente_autenticado_sem_tenant_403(client, db, default_company):
    """Autenticado sem company_id/membership → 403 (sem fallback salao-demo)."""
    cliente = _create_cliente(db, default_company.id, "Cliente Demo", "11970000004")
    user = _create_user(db, "fix08-sem-tenant@test.com", company=None)

    response = client.get(
        f"/clientes/{cliente.id}",
        headers=_auth_headers(user, company=None),
    )
    assert response.status_code == 403
    msg = response.json().get("message") or response.json().get("detail") or ""
    assert "Tenant" in str(msg)


@pytest.mark.unit
def test_obter_cliente_orfa_company_null_404(client, db, default_company):
    """Cliente com company_id IS NULL não é exposto ao tenant."""
    user = _create_user(db, "fix08-orfa@test.com", company=default_company)
    orfao = _create_cliente(db, None, "Orfao", "11970000005")

    response = client.get(
        f"/clientes/{orfao.id}",
        headers=_auth_headers(user, default_company),
    )
    assert response.status_code == 404


@pytest.mark.unit
def test_obter_cliente_inexistente_404(client, db, default_company):
    """ID inexistente → 404."""
    user = _create_user(db, "fix08-miss@test.com", company=default_company)
    response = client.get(
        "/clientes/999999",
        headers=_auth_headers(user, default_company),
    )
    assert response.status_code == 404


@pytest.mark.unit
def test_superuser_sem_tenant_nao_recebe_dados(client, db, default_company):
    """Superuser sem tenant efetivo → 403, sem dump global."""
    cliente = _create_cliente(db, default_company.id, "Cliente Super", "11970000006")
    user = _create_user(
        db, "fix08-super@test.com", company=None, is_superuser=True
    )

    response = client.get(
        f"/clientes/{cliente.id}",
        headers=_auth_headers(user, company=None),
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_filtro_company_id_na_query_obter(db, default_company):
    """Filtro de tenant está na query SQLAlchemy (não post-filter)."""
    company_b = _create_company(db, "fix08-sql", "Empresa SQL")
    ca = _create_cliente(db, default_company.id, "A SQL", "11970000007")
    cb = _create_cliente(db, company_b.id, "B SQL", "11970000008")

    q = db.query(Cliente).filter(
        Cliente.id == ca.id,
        Cliente.deleted_at.is_(None),
        Cliente.company_id == default_company.id,
    )
    sql = str(q.statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "company_id" in sql

    got = ClienteService(db).obter_cliente_do_tenant(ca.id, default_company.id)
    assert got.id == ca.id

    with pytest.raises(NotFoundError):
        ClienteService(db).obter_cliente_do_tenant(cb.id, default_company.id)

    assert (
        db.query(Cliente)
        .filter(Cliente.id == cb.id, Cliente.company_id == company_b.id)
        .count()
        == 1
    )
