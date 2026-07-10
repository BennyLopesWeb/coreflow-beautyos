"""
Port de tokens JWT — Hexagonal Architecture (Identity).
"""
from typing import Optional, Protocol

from app.models.user import User


class TokenServicePort(Protocol):
    """
    Porta para emissão e validação de tokens.

    Implementação: JwtTokenService.
    """

    def build_claims(
        self,
        user: User,
        company_id: int,
        role: str,
    ) -> dict:
        """
        Monta claims do JWT.

        Args:
            user: Usuário autenticado.
            company_id: Tenant ativo.
            role: Papel RBAC.

        Returns:
            Dict de claims.
        """
        ...

    def create_access_token(self, claims: dict) -> str:
        """Gera access token."""
        ...

    def create_refresh_token(self, claims: dict) -> str:
        """Gera refresh token."""
        ...

    def decode(self, token: str) -> Optional[dict]:
        """Decodifica token ou retorna None."""
        ...
