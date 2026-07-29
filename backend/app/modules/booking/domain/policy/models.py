"""
Modelos ORM de política de booking e auditoria técnica (FIX-CONFIG-01).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.db.base import Base


class BookingPolicyConfig(Base):
    """
    Override de política de booking por empresa (tenant).

    ``company_id`` é obrigatório e único: não há linha global nula.
    Ausência de linha = defaults de instalação via resolver.

    Attributes:
        id: PK.
        company_id: Tenant (FK companies.id), único.
        policy_json: Documento parcial ou completo de override.
        version: Versão monotônica do documento.
        is_active: Se o override está ativo.
        updated_by_user_id: Último editor (opcional).
        created_at: Criação.
        updated_at: Última atualização.
    """

    __tablename__ = "booking_policy_config"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_booking_policy_config_company"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    policy_json = Column(JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class BookingPolicyAudit(Base):
    """
    Trilha de auditoria técnica de mudanças de política (estrutura para API futura).

    Attributes:
        id: PK.
        company_id: Tenant afetado.
        actor_user_id: Usuário que alterou (opcional em bootstrap).
        action: Ação (create/update/deactivate/resolve_fallback).
        before_json: Snapshot anterior.
        after_json: Snapshot posterior.
        reason: Motivo textual opcional.
        created_at: Timestamp do evento.
    """

    __tablename__ = "booking_policy_audit"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
