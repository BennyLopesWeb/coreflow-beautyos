"""
Adapters SQLAlchemy — repositórios do módulo Identity.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company, CompanySegment, CompanyPlan
from app.models.user_company import UserCompany, CompanyRole
from app.schemas.company import CompanyCreate
from app.modules.identity.domain.constants import (
    DEFAULT_COMPANY_SLUG,
    DEFAULT_COMPANY_NAME,
)


class SqlAlchemyUserRepository:
    """
    Implementação UserRepositoryPort com SQLAlchemy.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Busca usuário por e-mail.

        Args:
            email: E-mail normalizado.

        Returns:
            User ou None.
        """
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .first()
        )

    def find_by_id(self, user_id: int) -> Optional[User]:
        """
        Busca usuário por ID.

        Args:
            user_id: Identificador.

        Returns:
            User ou None.
        """
        return (
            self.db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .first()
        )

    def save(self, user: User) -> User:
        """
        Persiste usuário.

        Args:
            user: Entidade User.

        Returns:
            User atualizado.
        """
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_active(self) -> List[User]:
        """
        Lista usuários ativos.

        Returns:
            Lista de User.
        """
        return self.db.query(User).filter(User.deleted_at.is_(None)).all()


class SqlAlchemyCompanyRepository:
    """
    Implementação CompanyRepositoryPort com SQLAlchemy.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, company_id: int) -> Optional[Company]:
        """Busca empresa por ID."""
        return (
            self.db.query(Company)
            .filter(Company.id == company_id, Company.deleted_at.is_(None))
            .first()
        )

    def find_by_slug(self, slug: str) -> Optional[Company]:
        """Busca empresa por slug."""
        return (
            self.db.query(Company)
            .filter(Company.slug == slug, Company.deleted_at.is_(None))
            .first()
        )

    def list_active(self) -> List[Company]:
        """Lista empresas ativas ordenadas por nome."""
        return (
            self.db.query(Company)
            .filter(Company.ativo == True, Company.deleted_at.is_(None))
            .order_by(Company.nome)
            .all()
        )

    def save(self, company: Company) -> Company:
        """Persiste empresa."""
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def create_from_schema(self, data: CompanyCreate) -> Company:
        """
        Cria empresa a partir de DTO.

        Args:
            data: CompanyCreate validado.

        Returns:
            Company persistida.
        """
        company = Company(
            nome=data.nome,
            slug=data.slug,
            segmento=data.segmento,
            plano=data.plano,
            timezone=data.timezone,
            logo_url=data.logo_url,
            ativo=True,
        )
        return self.save(company)

    def ensure_default(self) -> Company:
        """
        Garante empresa demo padrão.

        Returns:
            Company existente ou recém-criada.
        """
        existing = self.find_by_slug(DEFAULT_COMPANY_SLUG)
        if existing:
            if not existing.plugin_id:
                existing.plugin_id = "beauty"
                self.db.commit()
                self.db.refresh(existing)
            return existing
        company = Company(
            nome=DEFAULT_COMPANY_NAME,
            slug=DEFAULT_COMPANY_SLUG,
            segmento=CompanySegment.TRANCISTA,
            plano=CompanyPlan.FREE,
            timezone="America/Sao_Paulo",
            plugin_id="beauty",
            ativo=True,
        )
        return self.save(company)


class SqlAlchemyMembershipRepository:
    """
    Implementação MembershipRepositoryPort com SQLAlchemy.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def find(self, user_id: int, company_id: int) -> Optional[UserCompany]:
        """Busca vínculo específico."""
        return (
            self.db.query(UserCompany)
            .filter(
                UserCompany.user_id == user_id,
                UserCompany.company_id == company_id,
            )
            .first()
        )

    def find_primary_for_user(self, user_id: int) -> Optional[UserCompany]:
        """
        Retorna membership prioritário (owner > professional > receptionist > customer).

        Args:
            user_id: ID do usuário.

        Returns:
            UserCompany ou None.
        """
        memberships = (
            self.db.query(UserCompany).filter(UserCompany.user_id == user_id).all()
        )
        if not memberships:
            return None
        priority = {
            CompanyRole.OWNER: 0,
            CompanyRole.PROFESSIONAL: 1,
            CompanyRole.RECEPTIONIST: 2,
            CompanyRole.CUSTOMER: 3,
        }
        return sorted(memberships, key=lambda m: priority.get(m.role, 99))[0]

    def save(self, membership: UserCompany) -> UserCompany:
        """Persiste vínculo."""
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def assign(
        self, user: User, company: Company, role: CompanyRole
    ) -> UserCompany:
        """
        Associa usuário à empresa (idempotente).

        Args:
            user: Usuário.
            company: Empresa.
            role: Papel RBAC.

        Returns:
            UserCompany criado ou atualizado.
        """
        existing = self.find(user.id, company.id)
        if existing:
            existing.role = role
            self.db.commit()
            self.db.refresh(existing)
            return existing
        membership = UserCompany(
            user_id=user.id,
            company_id=company.id,
            role=role,
        )
        return self.save(membership)
