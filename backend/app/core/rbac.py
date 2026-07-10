"""
Compatibilidade legada — re-export RBAC do shared kernel.
"""
from app.shared.kernel.rbac import (
    is_admin_role,
    can_manage_catalog,
    can_manage_reservations,
    can_view_finance,
)

__all__ = [
    "is_admin_role",
    "can_manage_catalog",
    "can_manage_reservations",
    "can_view_finance",
]
