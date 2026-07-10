"""
Definições declarativas de workflow CoreFlow (YAML → Pydantic).
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStepDefinition(BaseModel):
    """
    Passo executável dentro de um workflow.

    Attributes:
        action: Nome da ação registrada no engine (ex.: notify_admin).
        params: Parâmetros opcionais da ação.
        when: Condição simples (always | deposit_paid).
    """

    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    when: str = "always"


class WorkflowDefinition(BaseModel):
    """
    Workflow declarativo carregado de YAML.

    Attributes:
        workflow_id: Identificador único do fluxo.
        name: Nome legível.
        plugin_id: Plugin associado (beauty, sports…).
        trigger: event_type que dispara o workflow.
        steps: Lista ordenada de passos.
        enabled: Se False, workflow ignorado.
    """

    workflow_id: str
    name: str = ""
    plugin_id: str = "beauty"
    trigger: str
    steps: List[WorkflowStepDefinition] = Field(default_factory=list)
    enabled: bool = True
