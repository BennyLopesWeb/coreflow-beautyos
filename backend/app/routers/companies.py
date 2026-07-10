"""
Compatibilidade legada — router delegado ao módulo Identity.
"""
from app.modules.identity.api.companies_router import router

__all__ = ["router"]
