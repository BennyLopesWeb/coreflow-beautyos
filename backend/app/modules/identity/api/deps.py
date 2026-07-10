"""
Dependências FastAPI do módulo Identity.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Header, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.identity.application.identity_service import IdentityApplicationService
from app.modules.identity.domain.constants import DEFAULT_COMPANY_SLUG
from app.shared.kernel.tenant import TenantContext

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


def get_identity_service(db: Session = Depends(get_db)) -> IdentityApplicationService:
    """
    Factory do serviço de aplicação Identity.

    Args:
        db: Sessão SQLAlchemy.

    Returns:
        IdentityApplicationService configurado.
    """
    return IdentityApplicationService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    identity: IdentityApplicationService = Depends(get_identity_service),
) -> User:
    """
    Valida JWT e retorna usuário autenticado.

    Args:
        credentials: Bearer token.
        identity: Serviço Identity.

    Returns:
        User ativo.
    """
    payload = identity.tokens.decode(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = identity.get_user_by_id(int(payload.get("sub")))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Usuário ativo autenticado."""
    return current_user


def _resolve_tenant(
    identity: IdentityApplicationService,
    user: Optional[User],
    company_slug: Optional[str],
    token_payload: Optional[dict],
) -> TenantContext:
    """
    Resolve TenantContext a partir de JWT, user ou slug público.

    Args:
        identity: Serviço Identity.
        user: Usuário autenticado opcional.
        company_slug: Slug explícito.
        token_payload: Payload JWT decodificado.

    Returns:
        TenantContext da requisição.
    """
    if token_payload and token_payload.get("company_id"):
        company = identity.get_company_by_id(int(token_payload["company_id"]))
        role_value = token_payload.get("role")
        role = CompanyRole(role_value) if role_value else None
        return TenantContext(
            company_id=company.id,
            company_slug=company.slug,
            user=user,
            role=role,
        )

    if user:
        membership = identity.get_primary_membership(user.id)
        if membership:
            company = identity.get_company_by_id(membership.company_id)
            return TenantContext(
                company_id=company.id,
                company_slug=company.slug,
                user=user,
                role=membership.role,
            )

    slug = company_slug or DEFAULT_COMPANY_SLUG
    company = identity.get_company_by_slug(slug)
    return TenantContext(
        company_id=company.id,
        company_slug=company.slug,
        user=user,
        role=None,
    )


def get_tenant_context(
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    x_company_slug: Optional[str] = Header(None, alias="X-Company-Slug"),
    company_slug: Optional[str] = Query(None, alias="company"),
) -> TenantContext:
    """
    Resolve tenant para rotas públicas ou autenticadas.

    Returns:
        TenantContext.
    """
    user: Optional[User] = None
    payload: Optional[dict] = None

    if credentials:
        payload = identity.tokens.decode(credentials.credentials)
        if payload and payload.get("type") == "access":
            user = identity.get_user_by_id(int(payload.get("sub")))

    slug = x_company_slug or company_slug
    return _resolve_tenant(identity, user, slug, payload)


def get_current_admin(
    tenant: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Exige permissão administrativa no tenant."""
    if not tenant.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores da empresa",
        )
    return tenant


def get_current_platform_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Exige superuser da plataforma."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores da plataforma",
        )
    return current_user


def get_current_admin_user(
    tenant: TenantContext = Depends(get_current_admin),
) -> User:
    """Retorna User para routers legados que esperam User admin."""
    if tenant.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária",
        )
    return tenant.user
