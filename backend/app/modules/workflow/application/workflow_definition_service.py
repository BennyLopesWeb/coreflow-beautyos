"""
Serviço de definições e configuração de workflows (editor admin proto).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.modules.workflow.domain.config_models import CoreWorkflowConfig
from app.modules.workflow.domain.definition import WorkflowDefinition
from app.modules.workflow.engine.workflow_engine import workflow_engine


class WorkflowDefinitionService:
    """
    Expõe workflows YAML para UI admin e persiste overrides de habilitação.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_definitions(self, company_id: int) -> List[Dict[str, Any]]:
        """
        Lista definições de workflow com estado efetivo de habilitação.

        Args:
            company_id: Tenant (para override por empresa).

        Returns:
            Lista de dicts serializáveis para frontend.
        """
        result: List[Dict[str, Any]] = []
        for defn in workflow_engine.list_definitions():
            effective = self.is_enabled(defn.workflow_id, company_id, defn.enabled)
            result.append(self._serialize(defn, effective))
        return result

    def get_definition(
        self, workflow_id: str, company_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém uma definição de workflow por ID.

        Args:
            workflow_id: ID do workflow YAML.
            company_id: Tenant.

        Returns:
            Dict serializável ou None.
        """
        defn = workflow_engine.get_definition(workflow_id)
        if not defn:
            return None
        effective = self.is_enabled(defn.workflow_id, company_id, defn.enabled)
        return self._serialize(defn, effective)

    def set_enabled(
        self,
        workflow_id: str,
        enabled: bool,
        company_id: Optional[int] = None,
    ) -> CoreWorkflowConfig:
        """
        Persiste override de habilitação (editor admin proto).

        Args:
            workflow_id: ID do workflow.
            enabled: Novo estado.
            company_id: Tenant (None = global plataforma).

        Returns:
            CoreWorkflowConfig persistido.
        """
        row = (
            self.db.query(CoreWorkflowConfig)
            .filter(
                CoreWorkflowConfig.workflow_id == workflow_id,
                CoreWorkflowConfig.company_id == company_id,
            )
            .first()
        )
        if row:
            row.enabled = enabled
        else:
            row = CoreWorkflowConfig(
                workflow_id=workflow_id,
                company_id=company_id,
                enabled=enabled,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def is_enabled(
        self,
        workflow_id: str,
        company_id: int,
        yaml_enabled: bool,
    ) -> bool:
        """
        Resolve habilitação efetiva (override DB > YAML).

        Args:
            workflow_id: ID do workflow.
            company_id: Tenant.
            yaml_enabled: Valor default do YAML.

        Returns:
            True se workflow deve executar.
        """
        if not yaml_enabled:
            return False
        override = (
            self.db.query(CoreWorkflowConfig)
            .filter(
                CoreWorkflowConfig.workflow_id == workflow_id,
                CoreWorkflowConfig.company_id == company_id,
            )
            .first()
        )
        if override is not None:
            return override.enabled
        global_override = (
            self.db.query(CoreWorkflowConfig)
            .filter(
                CoreWorkflowConfig.workflow_id == workflow_id,
                CoreWorkflowConfig.company_id.is_(None),
            )
            .first()
        )
        if global_override is not None:
            return global_override.enabled
        return yaml_enabled

    def _serialize(
        self, defn: WorkflowDefinition, effective_enabled: bool
    ) -> Dict[str, Any]:
        """
        Serializa WorkflowDefinition para resposta HTTP.

        Args:
            defn: Definição carregada do YAML.
            effective_enabled: Estado efetivo após overrides.

        Returns:
            Dict JSON-serializável.
        """
        return {
            "workflow_id": defn.workflow_id,
            "name": defn.name,
            "plugin_id": defn.plugin_id,
            "trigger": defn.trigger,
            "enabled": effective_enabled,
            "yaml_enabled": defn.enabled,
            "steps": [
                {
                    "action": s.action,
                    "when": s.when,
                    "params": s.params,
                }
                for s in defn.steps
            ],
        }
