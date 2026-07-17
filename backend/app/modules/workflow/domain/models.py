"""
Entidade ORM de execução de workflow CoreFlow.
"""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class WorkflowRunStatus(str, enum.Enum):
    """Status de uma execução de workflow."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CoreWorkflowRun(Base):
    """
    Registro de auditoria de execução de workflow.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        workflow_id: ID do workflow YAML.
        trigger_event_type: Evento que disparou a execução.
        trigger_event_id: UUID do evento de domínio.
        aggregate_id: ID da entidade raiz (booking, payment…).
        status: running | completed | failed.
        steps_executed: Log textual dos passos executados.
        error_message: Detalhe de falha opcional.
    """

    __tablename__ = "core_workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workflow_id = Column(String(255), nullable=False, index=True)
    trigger_event_type = Column(String(255), nullable=False, index=True)
    trigger_event_id = Column(String(255), nullable=True, index=True)
    aggregate_id = Column(String(255), nullable=True, index=True)
    status = Column(
        enum_values(WorkflowRunStatus),
        default=WorkflowRunStatus.RUNNING,
        nullable=False,
        index=True,
    )
    steps_executed = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
