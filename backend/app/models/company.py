"""
Model Company (tenant BeautyOS).
Representa uma empresa / negócio na plataforma multi-tenant.
"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class CompanySegment(str, enum.Enum):
    """Segmento de atuação da empresa na plataforma."""

    TRANCISTA = "trancista"
    BARBEARIA = "barbearia"
    SALAO = "salao"
    MANICURE = "manicure"
    LASH = "lash"
    ESTETICA = "estetica"
    MAQUIAGEM = "maquiagem"
    TATUAGEM = "tatuagem"


class CompanyPlan(str, enum.Enum):
    """Plano SaaS contratado pela empresa."""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company(Base):
    """
    Empresa (tenant) na plataforma BeautyOS.

    Cada registro representa um negócio isolado logicamente.
    Todas as entidades operacionais possuem ``company_id`` referenciando esta tabela.

    Attributes:
        id: Identificador interno.
        nome: Nome comercial exibido ao cliente.
        slug: Identificador único na URL e APIs públicas.
        segmento: Nicho de beleza (trancista, barbearia, etc.).
        plano: Plano SaaS (free, starter, pro, enterprise).
        timezone: Fuso horário IANA (ex.: America/Sao_Paulo).
        logo_url: URL opcional do logotipo.
        plugin_id: Plugin CoreFlow ativo (ex.: beauty, sports, clinic).
        ativo: Se a empresa está ativa na plataforma.
    """

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    segmento = Column(
        SQLEnum(CompanySegment),
        default=CompanySegment.TRANCISTA,
        nullable=False,
    )
    plano = Column(
        SQLEnum(CompanyPlan),
        default=CompanyPlan.FREE,
        nullable=False,
    )
    timezone = Column(String, default="America/Sao_Paulo", nullable=False)
    logo_url = Column(String, nullable=True)
    plugin_id = Column(String, default="beauty", nullable=False, index=True)
    ativo = Column(Boolean, default=True, nullable=False)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    memberships = relationship("UserCompany", back_populates="company")
