"""
Compatibilidade legada — delega ao módulo Identity (DDD v3.0).

Use ``IdentityApplicationService`` diretamente em código novo.
"""
from sqlalchemy.orm import Session

from app.modules.identity.application.identity_service import IdentityApplicationService


class AuthService(IdentityApplicationService):
    """
    Wrapper legado sobre IdentityApplicationService.

    Mantém assinatura ``AuthService(db)`` usada por routers e testes antigos.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        super().__init__(db)

    def create_user(self, user_data):
        """Alias legado para register_user."""
        return self.register_user(user_data)

    def authenticate_user(self, login_data):
        """
        Autentica usuário retornando User ou None (compatibilidade legada).

        Args:
            login_data: Credenciais.

        Returns:
            User ou None se senha inválida.
        """
        from app.core.exceptions import ValidationError

        try:
            return self.authenticate(login_data)
        except ValidationError as exc:
            if "incorretos" in str(exc):
                return None
            raise
