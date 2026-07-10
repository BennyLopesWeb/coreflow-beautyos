"""
Schemas do agente inteligente de automação.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.agent_task import AgentTaskStatus, AgentTaskType


class AgentTaskResponse(BaseModel):
    """Resposta de tarefa do agente."""
    id: int
    tipo: AgentTaskType
    titulo: str
    descricao: str
    status: AgentTaskStatus
    referencia_id: Optional[int] = None
    resultado: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgenteExecutarResponse(BaseModel):
    """Resposta após executar automações do agente."""
    tarefas_criadas: int
    tarefas_executadas: int
    mensagem: str
    tarefas: list[AgentTaskResponse]
