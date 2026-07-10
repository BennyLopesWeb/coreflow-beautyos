"""
Compatibilidade legada — re-export TenantContext do shared kernel.
"""
from app.shared.kernel.tenant import TenantContext

__all__ = ["TenantContext"]
