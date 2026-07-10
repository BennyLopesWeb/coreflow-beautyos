"""
Model UserCompany — vínculo usuário ↔ empresa com papel RBAC.
"""
import enum
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class CompanyRole(str, enum.Enum):
    """
    Papéis RBAC dentro de uma empresa BeautyOS.

    - owner: proprietário — acesso total ao negócio
    - professional: profissional — agenda, atendimentos, CRM
    - receptionist: recepção — reservas, fila, clientes
    - customer: cliente final — reservas próprias, histórico
    """

    OWNER = "owner"
    PROFESSIONAL = "professional"
    RECEPTIONIST = "receptionist"
    CUSTOMER = "customer"


# Papéis com permissão administrativa (substituem is_superuser por tenant)
ADMIN_ROLES = frozenset(
    {
        CompanyRole.OWNER,
        CompanyRole.PROFESSIONAL,
        CompanyRole.RECEPTIONIST,
    }
)


class UserCompany(Base):
    """
    Associação N:N entre usuário e empresa com papel RBAC.

    Attributes:
        id: Identificador interno.
        user_id: FK para ``users``.
        company_id: FK para ``companies``.
        role: Papel do usuário nesta empresa.
    """

    __tablename__ = "user_companies"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    role = Column(
        SQLEnum(CompanyRole),
        default=CompanyRole.CUSTOMER,
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="memberships")
    company = relationship("Company", back_populates="memberships")
