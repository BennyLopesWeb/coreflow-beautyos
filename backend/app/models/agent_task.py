"""
Model AgentTask
Tarefas automatizadas do agente inteligente de CRM/atendimento.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class AgentTaskStatus(str, enum.Enum):
    """Status de uma tarefa do agente."""
    PENDENTE = "pendente"
    EXECUTADA = "executada"
    CANCELADA = "cancelada"


class AgentTaskType(str, enum.Enum):
    """Tipo de tarefa automatizada."""
    LEMBRETE_PAGAMENTO = "lembrete_pagamento"
    REATIVAR_CLIENTE = "reativar_cliente"
    NOTIFICAR_FILA = "notificar_fila"
    CONFIRMAR_AGENDAMENTO = "confirmar_agendamento"
    FOLLOW_UP = "follow_up"


class AgentTask(Base):
    """
    Tarefa gerada ou executada pelo agente inteligente.

    Armazena ações sugeridas/automatizadas para CRM, pagamentos e fila.
    """
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    tipo = Column(SQLEnum(AgentTaskType), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=False)
    status = Column(SQLEnum(AgentTaskStatus), default=AgentTaskStatus.PENDENTE, nullable=False)
    referencia_id = Column(Integer, nullable=True)
    resultado = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_at = Column(DateTime(timezone=True), nullable=True)
