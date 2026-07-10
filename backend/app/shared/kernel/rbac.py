"""
RBAC — shared kernel BeautyOS.
"""
from app.models.user_company import CompanyRole, ADMIN_ROLES


def is_admin_role(role: CompanyRole) -> bool:
    """
    Verifica se o papel possui permissões administrativas no tenant.

    Args:
        role: Papel RBAC do usuário na empresa.

    Returns:
        True se owner, professional ou receptionist.
    """
    return role in ADMIN_ROLES


def can_manage_catalog(role: CompanyRole) -> bool:
    """
    Permite CRUD de catálogo e configurações comerciais.

    Args:
        role: Papel RBAC.

    Returns:
        True para owner e professional.
    """
    return role in {CompanyRole.OWNER, CompanyRole.PROFESSIONAL}


def can_manage_reservations(role: CompanyRole) -> bool:
    """
    Permite aprovar, rejeitar e gerenciar reservas.

    Args:
        role: Papel RBAC.

    Returns:
        True para papéis administrativos.
    """
    return role in ADMIN_ROLES


def can_view_finance(role: CompanyRole) -> bool:
    """
    Permite visualizar e registrar movimentos financeiros.

    Args:
        role: Papel RBAC.

    Returns:
        True para owner e professional.
    """
    return role in {CompanyRole.OWNER, CompanyRole.PROFESSIONAL}
