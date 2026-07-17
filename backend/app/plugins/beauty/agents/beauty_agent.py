"""
BeautyAgent — agente IA do plugin BeautyOS (R2-F4 / ADR-011).

Vive em ``app.plugins.beauty.agents`` (não em ``modules/ai``).
Orquestra análises CRM/atendimento via manifest e ``AgenteService`` legado.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.models.agent_task import AgentTask
from app.services.agente_service import AgenteService

logger = get_logger("beauty_agent")


@dataclass
class AgentAnalyzeResult:
    """
    Resultado de uma rodada de análise do BeautyAgent.

    Attributes:
        plugin_id: Plugin que originou a análise.
        tasks_created: Tarefas novas criadas nesta execução.
        pending_tasks: Total de tarefas pendentes após análise.
        capabilities: Capacidades IA declaradas no manifest.
        insights: Sugestões textuais geradas pelo protótipo.
    """

    plugin_id: str
    tasks_created: int
    pending_tasks: int
    capabilities: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa resultado para resposta HTTP.

        Returns:
            Dict JSON-serializável.
        """
        return {
            "plugin_id": self.plugin_id,
            "tasks_created": self.tasks_created,
            "pending_tasks": self.pending_tasks,
            "capabilities": self.capabilities,
            "insights": self.insights,
        }


class BeautyAgent:
    """
    Agente IA protótipo acoplado ao plugin BeautyOS.

    Usa ``ai_capabilities`` do manifest para decidir quais automações
    habilitar e delega persistência/execução ao ``AgenteService`` existente.

    Args:
        db: Sessão SQLAlchemy.
        plugin_id: ID do plugin (default beauty).
    """

    def __init__(self, db: Session, plugin_id: str = "beauty"):
        self.db = db
        self.plugin_id = plugin_id
        self.manifest = plugin_registry.require(plugin_id)
        self._legacy = AgenteService(db)

    def analyze(self, company_id: int) -> AgentAnalyzeResult:
        """
        Executa ciclo de análise CRM/atendimento para o tenant.

        Cria tarefas pendentes conforme capacidades IA do manifest e
        retorna resumo com insights textuais (protótipo, sem LLM externo).

        Args:
            company_id: ID da empresa (tenant).

        Returns:
            AgentAnalyzeResult com contadores e insights.
        """
        capabilities = list(self.manifest.ai_capabilities)
        tasks_created = 0

        if self.manifest.has_ai_capability("crm_followup"):
            tasks_created += self._legacy.analisar_e_criar_tarefas()
        elif self.manifest.has_feature("ai_crm"):
            tasks_created += self._legacy.analisar_e_criar_tarefas()

        pending = self._legacy.listar_tarefas(apenas_pendentes=True)
        insights = self._generate_insights(company_id, pending, capabilities)

        logger.info(
            f"[BeautyAgent] company={company_id} created={tasks_created} "
            f"pending={len(pending)} caps={capabilities}"
        )
        return AgentAnalyzeResult(
            plugin_id=self.plugin_id,
            tasks_created=tasks_created,
            pending_tasks=len(pending),
            capabilities=capabilities,
            insights=insights,
        )

    def list_tasks(
        self,
        company_id: int,
        pending_only: bool = False,
    ) -> List[AgentTask]:
        """
        Lista tarefas do agente filtradas por tenant.

        Args:
            company_id: ID da empresa.
            pending_only: Se True, retorna apenas pendentes.

        Returns:
            Lista de AgentTask do tenant.
        """
        tasks = self._legacy.listar_tarefas(apenas_pendentes=pending_only)
        return [t for t in tasks if t.company_id in (None, company_id)]

    def _generate_insights(
        self,
        company_id: int,
        pending: List[AgentTask],
        capabilities: List[str],
    ) -> List[str]:
        """
        Gera insights via AI Platform LLMService (mock ou OpenAI).

        Args:
            company_id: Tenant analisado.
            pending: Tarefas pendentes atuais.
            capabilities: Capacidades IA do manifest.

        Returns:
            Lista de strings com sugestões.
        """
        from app.modules.ai.llm_service import LLMService

        provider = LLMService.get_provider()
        return provider.generate_insights(
            {
                "company_id": company_id,
                "pending_tasks": pending,
                "capabilities": capabilities,
                "plugin_id": self.plugin_id,
            }
        )
