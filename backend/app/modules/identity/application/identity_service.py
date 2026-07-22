"""
Camada de aplicação — casos de uso Identity (auth, companies, RBAC, tenant).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.user_company import UserCompany, CompanyRole
from app.schemas.auth import UserCreate, LoginRequest
from app.schemas.company import CompanyCreate, UserMeResponse
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.core.config import settings
from app.shared.events.event_bus import event_bus
from app.modules.identity.domain.events import user_registered, company_created
from app.modules.identity.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyMembershipRepository,
)
from app.modules.identity.infrastructure.security.jwt_token_service import JwtTokenService


class IdentityApplicationService:
    """
    Orquestra casos de uso do bounded context Identity.

    Centraliza autenticação, empresas, memberships e bootstrap de tenant.
    Substitui AuthService + CompanyService (Strangler Fig).

    Args:
        db: Sessão SQLAlchemy injetada.
    """

    def __init__(self, db: Session):
        self.db = db
        self.users = SqlAlchemyUserRepository(db)
        self.companies = SqlAlchemyCompanyRepository(db)
        self.memberships = SqlAlchemyMembershipRepository(db)
        self.tokens = JwtTokenService()

    # ── Auth ──────────────────────────────────────────────────────────

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Busca usuário por e-mail."""
        return self.users.find_by_email(email)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Busca usuário por ID."""
        return self.users.find_by_id(user_id)

    def register_user(self, data: UserCreate) -> User:
        """
        Registra novo usuário e associa ao tenant demo como customer.

        Args:
            data: Dados de cadastro.

        Returns:
            User criado.

        Raises:
            ConflictError: E-mail já em uso.
        """
        if self.users.find_by_email(data.email):
            raise ConflictError(f"Email {data.email} já está em uso")

        user = User(
            email=data.email,
            nome=data.nome,
            telefone=data.telefone,
            hashed_password=get_password_hash(data.password),
            ativo=True,
        )
        user = self.users.save(user)

        company = self.companies.ensure_default()
        membership = self.memberships.assign(user, company, CompanyRole.CUSTOMER)

        event_bus.publish(
            user_registered(
                company_id=company.id,
                user_id=user.id,
                email=user.email,
                role=membership.role.value,
            )
        )
        return user

    def authenticate(self, data: LoginRequest) -> User:
        """
        Valida credenciais de login.

        Args:
            data: E-mail e senha.

        Returns:
            User autenticado.

        Raises:
            ValidationError: Credenciais inválidas ou usuário inativo.
        """
        user = self.users.find_by_email(data.email)
        if not user:
            raise ValidationError("Email ou senha incorretos")
        if not user.ativo:
            raise ValidationError("Usuário inativo")
        if not verify_password(data.password, user.hashed_password):
            raise ValidationError("Email ou senha incorretos")
        return user

    def _resolve_token_context(self, user: User) -> tuple[int, str]:
        """
        Resolve company_id e role para claims JWT.

        Args:
            user: Usuário autenticado.

        Returns:
            Tupla (company_id, role_value).
        """
        membership = self.memberships.find_primary_for_user(user.id)
        if membership:
            return membership.company_id, membership.role.value

        company = self.companies.ensure_default()
        role = CompanyRole.OWNER if user.is_superuser else CompanyRole.CUSTOMER
        self.memberships.assign(user, company, role)
        return company.id, role.value

    def login(self, data: LoginRequest) -> dict:
        """
        Realiza login e retorna tokens JWT com tenant.

        Args:
            data: Credenciais.

        Returns:
            Dict TokenResponse.
        """
        user = self.authenticate(data)
        company_id, role = self._resolve_token_context(user)
        claims = self.tokens.build_claims(user, company_id, role)
        return {
            "access_token": self.tokens.create_access_token(claims),
            "refresh_token": self.tokens.create_refresh_token(claims),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Gera novo access token a partir do refresh token.

        Args:
            refresh_token: Token refresh JWT.

        Returns:
            Dict com access_token.
        """
        payload = self.tokens.decode(refresh_token)
        if not payload:
            raise ValidationError("Refresh token inválido")
        if payload.get("type") != "refresh":
            raise ValidationError("Token não é um refresh token")

        user_id = int(payload.get("sub"))
        user = self.users.find_by_id(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))
        if not user.ativo:
            raise ValidationError("Usuário inativo")

        company_id, role = self._resolve_token_context(user)
        claims = self.tokens.build_claims(user, company_id, role)
        return {
            "access_token": self.tokens.create_access_token(claims),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def get_user_profile(self, user: User) -> UserMeResponse:
        """
        Monta perfil /me com contexto de tenant.

        Args:
            user: Usuário autenticado.

        Returns:
            UserMeResponse.
        """
        membership = self.memberships.find_primary_for_user(user.id)
        payload = {
            "id": user.id,
            "email": user.email,
            "nome": user.nome,
            "telefone": user.telefone,
            "ativo": user.ativo,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "company_id": None,
            "company_slug": None,
            "role": None,
        }
        if membership:
            company = self.companies.find_by_id(membership.company_id)
            if company:
                payload["company_id"] = company.id
                payload["company_slug"] = company.slug
                payload["role"] = membership.role
        return UserMeResponse(**payload)

    # ── Companies ─────────────────────────────────────────────────────

    def get_company_by_id(self, company_id: int) -> Company:
        """
        Obtém empresa por ID.

        Raises:
            NotFoundError: Se não existir.
        """
        company = self.companies.find_by_id(company_id)
        if not company:
            raise NotFoundError("Company", str(company_id))
        return company

    def get_company_by_slug(self, slug: str) -> Company:
        """
        Obtém empresa por slug.

        Raises:
            NotFoundError: Se não existir.
        """
        company = self.companies.find_by_slug(slug)
        if not company:
            raise NotFoundError("Company", slug)
        return company

    def list_active_companies(self) -> List[Company]:
        """Lista empresas ativas."""
        return self.companies.list_active()

    def create_company(self, data: CompanyCreate) -> Company:
        """
        Cria nova empresa.

        Raises:
            ConflictError: Slug duplicado.
        """
        if self.companies.find_by_slug(data.slug):
            raise ConflictError(f"Slug '{data.slug}' já está em uso")
        company = self.companies.create_from_schema(data)
        event_bus.publish(
            company_created(company.id, company.slug, company.nome)
        )
        return company

    def ensure_default_company(self) -> Company:
        """Garante tenant demo padrão."""
        return self.companies.ensure_default()

    def get_membership(
        self, user_id: int, company_id: int
    ) -> Optional[UserCompany]:
        """Busca membership específico."""
        return self.memberships.find(user_id, company_id)

    def get_primary_membership(self, user_id: int) -> Optional[UserCompany]:
        """Membership principal do usuário."""
        return self.memberships.find_primary_for_user(user_id)

    def assign_user(
        self, user: User, company: Company, role: CompanyRole
    ) -> UserCompany:
        """Associa usuário à empresa."""
        return self.memberships.assign(user, company, role)

    def sync_legacy_users(self, company: Company) -> int:
        """
        Vincula usuários legados sem membership.

        Returns:
            Quantidade processada.
        """
        count = 0
        for user in self.users.list_active():
            role = CompanyRole.OWNER if user.is_superuser else CompanyRole.CUSTOMER
            self.memberships.assign(user, company, role)
            count += 1
        return count

    def backfill_company_id(self, company_id: int) -> None:
        """
        Preenche company_id em entidades operacionais legadas.

        .. deprecated:: 2.11.0-r4-f8
            ``Agendamento`` removido da lista de models — a tabela
            ``agendamentos`` foi removida (DROP físico — ADR-024 sunset /
            RFC-003 M11+); ``self.db.query(Agendamento)`` levantaria erro
            imediatamente (classe não mapeada).

        Args:
            company_id: ID do tenant padrão.
        """
        from app.models.tranca import Tranca
        from app.models.cliente import Cliente
        from app.models.fila import Fila
        from app.models.agenda_dia import AgendaDia
        from app.models.schedule import Schedule
        from app.models.queue_entry import QueueEntry
        from app.models.financeiro import Financeiro
        from app.models.agent_task import AgentTask

        for model in (
            Tranca,
            Cliente,
            Fila,
            AgendaDia,
            Schedule,
            QueueEntry,
            Financeiro,
            AgentTask,
        ):
            self.db.query(model).filter(model.company_id.is_(None)).update(
                {model.company_id: company_id},
                synchronize_session=False,
            )
        self.db.commit()

    # Aliases legados (AuthService / CompanyService)
    create_user = register_user
    obter_por_id = get_company_by_id
    obter_por_slug = get_company_by_slug
    listar_ativas = list_active_companies
    criar = create_company
