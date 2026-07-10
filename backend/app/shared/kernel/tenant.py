"""
Contexto de tenant (empresa) — shared kernel BeautyOS.
"""
from dataclasses import dataclass
from typing import Optional

from app.models.user import User
from app.models.user_company import CompanyRole


@dataclass(frozen=True)
class TenantContext:
    """
    Contexto resolvido da empresa ativa na requisição.

    Attributes:
        company_id: ID da empresa (tenant).
        company_slug: Slug público da empresa.
        user: Usuário autenticado, se houver.
        role: Papel RBAC na empresa, se autenticado.
    """

    company_id: int
    company_slug: str
    user: Optional[User] = None
    role: Optional[CompanyRole] = None

    def is_admin(self) -> bool:
        """
        Indica se o contexto tem permissão administrativa.

        Returns:
            True se superuser legado ou papel administrativo RBAC.
        """
        if self.user and self.user.is_superuser:
            return True
        if self.role is None:
            return False
        from app.shared.kernel.rbac import is_admin_role

        return is_admin_role(self.role)
