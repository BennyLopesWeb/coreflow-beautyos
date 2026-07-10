"""
Testes do módulo Company e RBAC (BeautyOS Fase A).
"""
import pytest

from app.models.user import User
from app.models.user_company import CompanyRole
from app.services.company_service import CompanyService, DEFAULT_COMPANY_SLUG
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest
from app.core.security import decode_token, get_password_hash
from app.core.rbac import is_admin_role, can_manage_catalog


@pytest.fixture
def default_company(db):
    """
    Empresa demo padrão para testes multi-tenant.

    Args:
        db: Sessão de teste.

    Returns:
        Company criada ou existente.
    """
    return CompanyService(db).ensure_default_company()


def test_ensure_default_company(db):
    """Garante criação idempotente da empresa demo."""
    svc = CompanyService(db)
    c1 = svc.ensure_default_company()
    c2 = svc.ensure_default_company()
    assert c1.id == c2.id
    assert c1.slug == DEFAULT_COMPANY_SLUG


def test_assign_user_owner(db, default_company):
    """Vincula usuário como owner na empresa."""
    user = User(
        email="owner@test.com",
        nome="Owner",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    membership = CompanyService(db).assign_user(user, default_company, CompanyRole.OWNER)
    assert membership.role == CompanyRole.OWNER
    assert membership.company_id == default_company.id


def test_login_token_includes_tenant(db, default_company):
    """Login inclui company_id e role no JWT."""
    user = User(
        email="pro@test.com",
        nome="Pro",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    CompanyService(db).assign_user(user, default_company, CompanyRole.OWNER)

    tokens = AuthService(db).login(LoginRequest(email="pro@test.com", password="123456"))
    payload = decode_token(tokens["access_token"])
    assert payload["company_id"] == default_company.id
    assert payload["role"] == "owner"


def test_rbac_admin_roles():
    """Papéis administrativos RBAC."""
    assert is_admin_role(CompanyRole.OWNER) is True
    assert is_admin_role(CompanyRole.RECEPTIONIST) is True
    assert is_admin_role(CompanyRole.CUSTOMER) is False
    assert can_manage_catalog(CompanyRole.PROFESSIONAL) is True
    assert can_manage_catalog(CompanyRole.CUSTOMER) is False


def test_backfill_company_id(db, default_company):
    """Backfill preenche company_id em registros legados."""
    from app.models.tranca import Tranca

    tranca = Tranca(nome="Teste Tenant", ativo=True, company_id=None)
    db.add(tranca)
    db.commit()

    CompanyService(db).backfill_company_id(default_company.id)
    db.refresh(tranca)
    assert tranca.company_id == default_company.id


def test_list_companies_public(client, default_company):
    """Endpoint público lista empresas ativas."""
    response = client.get("/companies")
    assert response.status_code == 200
    data = response.json()
    assert any(c["slug"] == DEFAULT_COMPANY_SLUG for c in data)
