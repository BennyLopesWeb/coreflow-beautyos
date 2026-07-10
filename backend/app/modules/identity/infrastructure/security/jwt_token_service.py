"""
Adapter JWT — implementação TokenServicePort.
"""
from typing import Optional

from app.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


class JwtTokenService:
    """
    Emite e decodifica tokens JWT para o módulo Identity.

    Implementa TokenServicePort.
    """

    def build_claims(
        self,
        user: User,
        company_id: int,
        role: str,
    ) -> dict:
        """
        Monta claims padrão BeautyOS.

        Args:
            user: Usuário autenticado.
            company_id: Tenant ativo.
            role: Valor do enum CompanyRole.

        Returns:
            Dict para encode JWT.
        """
        return {
            "sub": str(user.id),
            "email": user.email,
            "company_id": company_id,
            "role": role,
        }

    def create_access_token(self, claims: dict) -> str:
        """Gera access token."""
        return create_access_token(data=claims)

    def create_refresh_token(self, claims: dict) -> str:
        """Gera refresh token."""
        return create_refresh_token(data=claims)

    def decode(self, token: str) -> Optional[dict]:
        """Decodifica token."""
        return decode_token(token)
