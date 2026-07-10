"""
Compatibilidade legada — re-export dependências do módulo Identity.
"""
from app.modules.identity.api.deps import (
    get_identity_service,
    get_current_user,
    get_current_active_user,
    get_tenant_context,
    get_current_admin,
    get_current_platform_admin,
    get_current_admin_user,
    security,
    security_optional,
)

__all__ = [
    "get_identity_service",
    "get_current_user",
    "get_current_active_user",
    "get_tenant_context",
    "get_current_admin",
    "get_current_platform_admin",
    "get_current_admin_user",
    "security",
    "security_optional",
]
