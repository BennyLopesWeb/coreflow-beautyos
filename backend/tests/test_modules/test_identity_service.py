"""Testes do módulo Identity — DDD v3.0."""
from app.modules.identity.application.identity_service import IdentityApplicationService
from app.schemas.auth import UserCreate, LoginRequest
from app.core.security import get_password_hash
from app.models.user import User
from app.models.user_company import CompanyRole


def test_identity_service_register_and_login(db, default_company):
    """Registro e login via IdentityApplicationService."""
    identity = IdentityApplicationService(db)
    user = identity.register_user(
        UserCreate(
            email="novo@test.com",
            nome="Novo User",
            telefone="11988887777",
            password="123456",
        )
    )
    assert user.id is not None
    membership = identity.get_primary_membership(user.id)
    assert membership is not None
    assert membership.role == CompanyRole.CUSTOMER

    tokens = identity.login(LoginRequest(email="novo@test.com", password="123456"))
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_identity_ports_isolation(db):
    """Repositórios são injetados via IdentityApplicationService."""
    identity = IdentityApplicationService(db)
    assert identity.users is not None
    assert identity.companies is not None
    assert identity.memberships is not None
    assert identity.tokens is not None


def test_legacy_auth_service_wrapper(db):
    """AuthService legado delega ao módulo Identity."""
    from app.services.auth_service import AuthService

    svc = AuthService(db)
    user = User(
        email="legacy@test.com",
        nome="Legacy",
        hashed_password=get_password_hash("123456"),
        ativo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    from app.services.company_service import CompanyService

    CompanyService(db).assign_user(user, CompanyService(db).ensure_default_company(), CompanyRole.OWNER)

    result = svc.login(LoginRequest(email="legacy@test.com", password="123456"))
    assert result["access_token"]
