"""
Ports de repositório — Hexagonal Architecture (Identity).
"""
from typing import List, Optional, Protocol

from app.models.user import User
from app.models.company import Company
from app.models.user_company import UserCompany, CompanyRole
from app.schemas.company import CompanyCreate


class UserRepositoryPort(Protocol):
    """
    Porta de persistência de usuários.

    Implementação: SqlAlchemyUserRepository.
    """

    def find_by_email(self, email: str) -> Optional[User]:
        """Busca usuário ativo por e-mail."""
        ...

    def find_by_id(self, user_id: int) -> Optional[User]:
        """Busca usuário ativo por ID."""
        ...

    def save(self, user: User) -> User:
        """Persiste usuário."""
        ...

    def list_active(self) -> List[User]:
        """Lista usuários não deletados."""
        ...


class CompanyRepositoryPort(Protocol):
    """
    Porta de persistência de empresas (tenants).
    """

    def find_by_id(self, company_id: int) -> Optional[Company]:
        """Busca empresa por ID."""
        ...

    def find_by_slug(self, slug: str) -> Optional[Company]:
        """Busca empresa por slug."""
        ...

    def list_active(self) -> List[Company]:
        """Lista empresas ativas."""
        ...

    def save(self, company: Company) -> Company:
        """Persiste empresa."""
        ...

    def create_from_schema(self, data: CompanyCreate) -> Company:
        """Cria empresa a partir de DTO."""
        ...


class MembershipRepositoryPort(Protocol):
    """
    Porta de vínculos usuário ↔ empresa (RBAC).
    """

    def find(self, user_id: int, company_id: int) -> Optional[UserCompany]:
        """Busca membership específico."""
        ...

    def find_primary_for_user(self, user_id: int) -> Optional[UserCompany]:
        """Retorna membership prioritário do usuário."""
        ...

    def save(self, membership: UserCompany) -> UserCompany:
        """Persiste vínculo."""
        ...

    def assign(
        self, user: User, company: Company, role: CompanyRole
    ) -> UserCompany:
        """Associa usuário à empresa (idempotente)."""
        ...
