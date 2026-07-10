"""
Compatibilidade legada — delega ao módulo Identity (DDD v3.0).

Use ``IdentityApplicationService`` diretamente em código novo.
"""
from sqlalchemy.orm import Session

from app.modules.identity.application.identity_service import IdentityApplicationService
from app.modules.identity.domain.constants import (
    DEFAULT_COMPANY_SLUG,
    DEFAULT_COMPANY_NAME,
)

__all__ = ["CompanyService", "DEFAULT_COMPANY_SLUG", "DEFAULT_COMPANY_NAME"]


class CompanyService(IdentityApplicationService):
    """
    Wrapper legado sobre IdentityApplicationService.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        super().__init__(db)
