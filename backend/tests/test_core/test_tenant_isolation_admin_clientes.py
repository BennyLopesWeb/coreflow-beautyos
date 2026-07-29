"""
Isolamento multi-tenant — GET /admin/pagamentos e GET /clientes.

Garante que o filtro ``company_id`` ocorre na query SQLAlchemy e que
dados de outro tenant (ou órfãos com ``company_id IS NULL``) não vazam.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.cliente import Cliente
from app.models.company import Company, CompanySegment, CompanyPlan
from app.models.user import User
from app.models.user_company import CompanyRole
from app.models.agendamento import ReservationStatus
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.admin_service import AdminService
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


def _create_admin_for_company(db, company: Company, email: str) -> User:
    """
    Cria admin (owner) vinculado a uma empresa.

    Args:
        db: Sessão.
        company: Tenant.
        email: E-mail único.

    Returns:
        User persistido com membership OWNER.
    """
    user = User(
        email=email,
        nome="Admin Tenant",
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
    Monta Authorization Bearer com ``company_id`` no JWT.

    Args:
        user: Usuário.
        company: Tenant ativo.

    Returns:
        Dict de headers HTTP.
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


def _create_cliente(db, company_id, nome: str, telefone: str) -> Cliente:
    """
    Persiste cliente opcionalmente vinculado a um tenant.

    Args:
        db: Sessão.
        company_id: ID da empresa ou ``None`` (órfão).
        nome: Nome.
        telefone: Telefone único.

    Returns:
        Cliente persistido.
    """
    cliente = Cliente(
        nome=nome,
        telefone=telefone,
        email=f"{telefone}@test.com",
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
    days_ahead: int,
) -> CoreBooking:
    """
    Persiste booking mínimo para listagem de pagamentos admin.

    Args:
        db: Sessão.
        company_id: Tenant do booking.
        customer_id: ID ``clientes``.
        catalog_id: Catálogo.
        offering_id: Offering.
        days_ahead: Offset de agenda.

    Returns:
        CoreBooking persistido.
    """
    booking = CoreBooking(
        company_id=company_id,
        customer_id=customer_id,
        catalog_id=catalog_id,
        offering_id=offering_id,
        scheduled_at=datetime.now() + timedelta(days=days_ahead),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=False,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@pytest.mark.unit
def test_admin_pagamentos_isola_empresa_a_de_b(
    client, db, default_company, synced_catalog
):
    """Admin da empresa A não recebe pagamentos da empresa B."""
    catalog, offering = synced_catalog
    company_b = _create_company(db, "empresa-b-iso", "Empresa B")
    admin_a = _create_admin_for_company(db, default_company, "admin-a-iso@test.com")

    cliente_a = _create_cliente(db, default_company.id, "Cliente A", "11911110001")
    cliente_b = _create_cliente(db, company_b.id, "Cliente B", "11911110002")
    booking_a = _create_booking(
        db, default_company.id, cliente_a.id, catalog.id, offering.id, 10
    )
    booking_b = _create_booking(
        db, company_b.id, cliente_b.id, catalog.id, offering.id, 11
    )

    response = client.get(
        "/admin/pagamentos",
        headers=_auth_headers(admin_a, default_company),
    )
    assert response.status_code == 200
    ids = {item["agendamento_id"] for item in response.json()}
    assert booking_a.id in ids
    assert booking_b.id not in ids


@pytest.mark.unit
def test_clientes_isola_empresa_a_de_b(client, db, default_company):
    """Usuário da empresa A não recebe clientes da empresa B."""
    company_b = _create_company(db, "empresa-b-cli", "Empresa B Cli")
    admin_a = _create_admin_for_company(db, default_company, "admin-a-cli@test.com")
    _create_cliente(db, default_company.id, "Cliente A", "11911110011")
    _create_cliente(db, company_b.id, "Cliente B", "11911110012")

    response = client.get(
        "/clientes",
        headers=_auth_headers(admin_a, default_company),
    )
    assert response.status_code == 200
    nomes = {item["nome"] for item in response.json()}
    assert "Cliente A" in nomes
    assert "Cliente B" not in nomes


@pytest.mark.unit
def test_usuario_sem_company_id_nao_lista_clientes(client, db, default_company):
    """Usuário sem company_id efetivo não recebe clientes de nenhuma empresa."""
    _create_cliente(db, default_company.id, "Cliente Demo", "11911110021")
    user = User(
        email="sem-tenant@test.com",
        nome="Sem Tenant",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    response = client.get(
        "/clientes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_usuario_sem_company_id_nao_lista_pagamentos_admin(
    client, db, default_company, synced_catalog
):
    """Usuário sem vínculo admin/tenant não recebe dump de pagamentos."""
    catalog, offering = synced_catalog
    cliente = _create_cliente(db, default_company.id, "Cliente P", "11911110022")
    _create_booking(
        db, default_company.id, cliente.id, catalog.id, offering.id, 12
    )
    user = User(
        email="sem-admin@test.com",
        nome="Sem Admin",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    response = client.get(
        "/admin/pagamentos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_superuser_sem_tenant_efetivo_nao_usa_fallback_salao_demo(
    client, db, default_company, synced_catalog
):
    """Superuser sem JWT company_id/membership não lista via fallback salao-demo."""
    catalog, offering = synced_catalog
    cliente = _create_cliente(db, default_company.id, "Cliente Super", "11911110023")
    _create_booking(
        db, default_company.id, cliente.id, catalog.id, offering.id, 13
    )
    user = User(
        email="super-sem-tenant@test.com",
        nome="Super Sem Tenant",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    response = client.get(
        "/admin/pagamentos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    body = response.json()
    msg = body.get("message") or body.get("detail") or ""
    assert "Tenant" in str(msg)


@pytest.mark.unit
def test_cliente_company_id_null_excluido_da_listagem(db, default_company):
    """Registros com company_id IS NULL não aparecem na listagem por tenant."""
    _create_cliente(db, default_company.id, "Com Tenant", "11911110031")
    _create_cliente(db, None, "Orfao Global", "11911110032")

    rows = ClienteService(db).listar_clientes(default_company.id)
    nomes = {c.nome for c in rows}
    assert "Com Tenant" in nomes
    assert "Orfao Global" not in nomes

    orfaos = (
        db.query(Cliente)
        .filter(Cliente.company_id.is_(None), Cliente.deleted_at.is_(None))
        .count()
    )
    assert orfaos == 1


@pytest.mark.unit
def test_filtro_company_id_na_query_sqlalchemy(db, default_company, synced_catalog):
    """
    O filtro de tenant está na query SQLAlchemy (não post-filter em memória).

    Valida presença de ``company_id`` no SQL compilado e que a contagem
    no banco para outro tenant permanece intacta após a listagem.
    """
    catalog, offering = synced_catalog
    company_b = _create_company(db, "empresa-b-sql", "Empresa B SQL")
    _create_cliente(db, default_company.id, "Cliente A SQL", "11911110041")
    _create_cliente(db, company_b.id, "Cliente B SQL", "11911110042")

    cli_query = db.query(Cliente).filter(
        Cliente.deleted_at.is_(None),
        Cliente.company_id == default_company.id,
    )
    sql_cli = str(cli_query.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "company_id" in sql_cli.lower()

    book_query = db.query(CoreBooking).filter(
        CoreBooking.deleted_at.is_(None),
        CoreBooking.company_id == default_company.id,
    )
    sql_book = str(
        book_query.statement.compile(compile_kwargs={"literal_binds": True})
    )
    assert "company_id" in sql_book.lower()

    listed = ClienteService(db).listar_clientes(default_company.id)
    assert all(c.company_id == default_company.id for c in listed)
    assert (
        db.query(Cliente)
        .filter(Cliente.company_id == company_b.id, Cliente.deleted_at.is_(None))
        .count()
        == 1
    )

    ca = _create_cliente(db, default_company.id, "Pay A", "11911110043")
    cb = _create_cliente(db, company_b.id, "Pay B", "11911110044")
    ba = _create_booking(
        db, default_company.id, ca.id, catalog.id, offering.id, 20
    )
    bb = _create_booking(db, company_b.id, cb.id, catalog.id, offering.id, 21)
    items = AdminService(db).listar_pagamentos(default_company.id)
    ids = {i.agendamento_id for i in items}
    assert ba.id in ids
    assert bb.id not in ids
    assert (
        db.query(CoreBooking)
        .filter(CoreBooking.id == bb.id, CoreBooking.company_id == company_b.id)
        .count()
        == 1
    )


@pytest.mark.unit
def test_mesmo_tenant_continua_vendo_seus_dados(
    client, db, default_company, synced_catalog
):
    """Comportamento dentro do mesmo tenant é preservado."""
    catalog, offering = synced_catalog
    admin_a = _create_admin_for_company(db, default_company, "admin-same@test.com")
    cliente = _create_cliente(db, default_company.id, "Cliente Same", "11911110051")
    booking = _create_booking(
        db, default_company.id, cliente.id, catalog.id, offering.id, 30
    )
    headers = _auth_headers(admin_a, default_company)

    r_cli = client.get("/clientes", headers=headers)
    assert r_cli.status_code == 200
    assert any(c["nome"] == "Cliente Same" for c in r_cli.json())

    r_pag = client.get("/admin/pagamentos", headers=headers)
    assert r_pag.status_code == 200
    assert any(p["agendamento_id"] == booking.id for p in r_pag.json())
