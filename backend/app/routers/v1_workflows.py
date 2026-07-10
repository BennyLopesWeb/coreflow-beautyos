"""
Router API v1 — Workflow runs (auditoria de automações).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.workflow.domain.models import CoreWorkflowRun
from app.modules.workflow.application.workflow_definition_service import WorkflowDefinitionService
from app.schemas.coreflow_v1 import WorkflowDefinitionResponse, WorkflowConfigPatch
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/workflows", tags=["CoreFlow — Workflow"])


class WorkflowRunResponse(BaseModel):
    """
    Resposta de execução de workflow.

    Attributes:
        id: ID core_workflow_runs.
        workflow_id: ID do workflow YAML.
        trigger_event_type: Evento disparador.
        status: running | completed | failed.
        steps_executed: Passos executados.
        error_message: Erro opcional.
        created_at: Início da execução.
        completed_at: Fim da execução.
    """

    id: int
    workflow_id: str
    trigger_event_type: str
    status: str
    steps_executed: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/runs", response_model=List[WorkflowRunResponse])
def listar_workflow_runs(
    workflow_id: Optional[str] = Query(None, description="Filtra por workflow_id"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista execuções de workflow do tenant (auditoria).

    Args:
        workflow_id: Filtro opcional por ID do workflow.

    Returns:
        Lista de core_workflow_runs mais recentes.
    """
    query = db.query(CoreWorkflowRun).filter(
        CoreWorkflowRun.company_id == tenant.company_id
    )
    if workflow_id:
        query = query.filter(CoreWorkflowRun.workflow_id == workflow_id)
    rows = query.order_by(CoreWorkflowRun.created_at.desc()).limit(50).all()
    return rows


@router.get("/definitions", response_model=List[WorkflowDefinitionResponse])
def listar_workflow_definitions(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista definições YAML de workflows para editor admin (proto).

    Returns:
        Workflows com steps e estado efetivo de habilitação.
    """
    defs = WorkflowDefinitionService(db).list_definitions(tenant.company_id)
    return [WorkflowDefinitionResponse(**d) for d in defs]


@router.get("/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
def obter_workflow_definition(
    workflow_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de uma definição de workflow.

    Args:
        workflow_id: ID do workflow YAML.

    Returns:
        WorkflowDefinitionResponse.
    """
    row = WorkflowDefinitionService(db).get_definition(workflow_id, tenant.company_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' não encontrado")
    return WorkflowDefinitionResponse(**row)


@router.patch("/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
def atualizar_workflow_config(
    workflow_id: str,
    body: WorkflowConfigPatch,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Habilita/desabilita workflow por tenant (editor admin proto).

    Args:
        workflow_id: ID do workflow.
        body: Novo estado enabled.

    Returns:
        Definição atualizada com enabled efetivo.
    """
    if not WorkflowDefinitionService(db).get_definition(workflow_id, tenant.company_id):
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' não encontrado")
    WorkflowDefinitionService(db).set_enabled(
        workflow_id, body.enabled, company_id=tenant.company_id
    )
    row = WorkflowDefinitionService(db).get_definition(workflow_id, tenant.company_id)
    return WorkflowDefinitionResponse(**row)
