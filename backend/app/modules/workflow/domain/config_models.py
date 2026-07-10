"""
Configuração runtime de workflows (override admin sobre YAML).
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CoreWorkflowConfig(Base):
    """
    Override de habilitação de workflow por tenant ou plataforma.

    Attributes:
        id: Identificador interno.
        company_id: Tenant (null = override global da plataforma).
        workflow_id: ID do workflow YAML.
        enabled: Se False, workflow não executa mesmo se YAML enabled.
    """

    __tablename__ = "core_workflow_config"
    __table_args__ = (
        UniqueConstraint("company_id", "workflow_id", name="uq_workflow_config_company"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    workflow_id = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
