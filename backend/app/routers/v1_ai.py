"""
Router API v1 — AI Platform (protótipo BeautyAgent).
"""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.ai.beauty_agent import BeautyAgent
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.schemas.agente import AgentTaskResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/ai", tags=["CoreFlow — AI"])


class AgentAnalyzeResponse(BaseModel):
    """
    Resposta da análise do BeautyAgent.

    Attributes:
        plugin_id: Plugin que executou a análise.
        tasks_created: Tarefas criadas nesta execução.
        pending_tasks: Tarefas pendentes após análise.
        capabilities: Capacidades IA do manifest.
        insights: Sugestões textuais geradas.
    """

    plugin_id: str
    tasks_created: int
    pending_tasks: int
    capabilities: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)


@router.post("/analyze", response_model=AgentAnalyzeResponse)
def analisar_salao(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Executa ciclo de análise CRM/atendimento do BeautyAgent.

    Protótipo rule-based — futuras versões integrarão LLM via AI Platform.

    Returns:
        Resumo com tarefas criadas e insights.
    """
    result = BeautyAgent(db).analyze(tenant.company_id)
    return AgentAnalyzeResponse(**result.to_dict())


@router.get("/tasks", response_model=List[AgentTaskResponse])
def listar_tarefas_ia(
    pending_only: bool = True,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista tarefas do agente IA para o tenant.

    Args:
        pending_only: Se True, retorna apenas pendentes.

    Returns:
        Lista de AgentTaskResponse.
    """
    tasks = BeautyAgent(db).list_tasks(tenant.company_id, pending_only=pending_only)
    return [AgentTaskResponse.model_validate(t) for t in tasks]
