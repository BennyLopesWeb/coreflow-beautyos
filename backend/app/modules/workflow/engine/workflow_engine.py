"""
Workflow Engine — executa fluxos declarativos YAML reagindo a eventos de domínio.
"""
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.workflow.domain.definition import WorkflowDefinition, WorkflowStepDefinition
from app.modules.workflow.domain.models import CoreWorkflowRun, WorkflowRunStatus
from app.shared.events.domain_event import DomainEvent

logger = get_logger("workflow_engine")

ActionHandler = Callable[[Session, WorkflowStepDefinition, DomainEvent, CoreWorkflowRun], None]

WORKFLOWS_DIR = Path(__file__).resolve().parents[4] / "workflows"


class WorkflowEngine:
    """
    Motor de workflows event-driven CoreFlow.

    Carrega definições YAML de ``backend/workflows/`` e executa passos
    registrados quando eventos correspondentes são publicados no event bus.

    Args:
        workflows_dir: Diretório raiz de YAMLs (default backend/workflows).
    """

    def __init__(self, workflows_dir: Optional[Path] = None):
        self._workflows_dir = workflows_dir or WORKFLOWS_DIR
        self._definitions: List[WorkflowDefinition] = []
        self._actions: Dict[str, ActionHandler] = {}
        self._register_builtin_actions()

    def _register_builtin_actions(self) -> None:
        """
        Registra ações built-in disponíveis nos workflows YAML.

        Returns:
            None
        """
        self.register_action("log", self._action_log)
        self.register_action("notify_admin", self._action_notify_admin)

    def register_action(self, name: str, handler: ActionHandler) -> None:
        """
        Registra handler para uma ação de workflow.

        Args:
            name: Nome da ação (ex.: notify_admin).
            handler: Callable(db, step, event, run).

        Returns:
            None
        """
        self._actions[name] = handler

    def load_all(self) -> int:
        """
        Carrega todos os arquivos ``*.yaml`` do diretório de workflows.

        Returns:
            Quantidade de definições carregadas.
        """
        self._definitions.clear()
        if not self._workflows_dir.is_dir():
            logger.warning(f"Diretório workflows não encontrado: {self._workflows_dir}")
            return 0

        count = 0
        for path in sorted(self._workflows_dir.glob("*.yaml")):
            try:
                with open(path, encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)
                if isinstance(data, list):
                    for item in data:
                        defn = WorkflowDefinition(**item)
                        self._definitions.append(defn)
                        count += 1
                else:
                    defn = WorkflowDefinition(**data)
                    self._definitions.append(defn)
                    count += 1
                logger.info(f"Workflow carregado: {path.name}")
            except Exception as exc:
                logger.error(f"Erro ao carregar workflow {path}: {exc}")
        return count

    def all_triggers(self) -> List[str]:
        """
        Lista event_types que disparam algum workflow.

        Returns:
            Lista única de triggers.
        """
        return list({d.trigger for d in self._definitions})

    def list_definitions(self) -> List[WorkflowDefinition]:
        """
        Lista todas as definições carregadas (inclui desabilitadas no YAML).

        Returns:
            Lista de WorkflowDefinition.
        """
        return list(self._definitions)

    def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        Obtém definição por workflow_id.

        Args:
            workflow_id: Identificador do workflow.

        Returns:
            WorkflowDefinition ou None.
        """
        for defn in self._definitions:
            if defn.workflow_id == workflow_id:
                return defn
        return None

    def process_event(self, db: Session, event: DomainEvent) -> List[CoreWorkflowRun]:
        """
        Executa workflows cujo trigger coincide com o evento recebido.

        Args:
            db: Sessão SQLAlchemy.
            event: Evento de domínio publicado.

        Returns:
            Lista de CoreWorkflowRun criados/atualizados.
        """
        runs: List[CoreWorkflowRun] = []
        from app.modules.workflow.application.workflow_definition_service import (
            WorkflowDefinitionService,
        )

        def_svc = WorkflowDefinitionService(db)
        for defn in self._definitions:
            if defn.trigger != event.event_type:
                continue
            if not def_svc.is_enabled(defn.workflow_id, event.company_id, defn.enabled):
                logger.debug(
                    f"Workflow {defn.workflow_id} desabilitado — skip "
                    f"(company={event.company_id})"
                )
                continue
            run = self._execute_workflow(db, defn, event)
            if run:
                runs.append(run)
        return runs

    def _execute_workflow(
        self,
        db: Session,
        defn: WorkflowDefinition,
        event: DomainEvent,
    ) -> Optional[CoreWorkflowRun]:
        """
        Executa um workflow específico para um evento.

        Args:
            db: Sessão SQLAlchemy.
            defn: Definição YAML.
            event: Evento disparador.

        Returns:
            CoreWorkflowRun persistido ou None se falhar antes de criar run.
        """
        run = CoreWorkflowRun(
            company_id=event.company_id,
            workflow_id=defn.workflow_id,
            trigger_event_type=event.event_type,
            trigger_event_id=event.event_id,
            aggregate_id=event.aggregate_id,
            status=WorkflowRunStatus.RUNNING,
            steps_executed="",
        )
        db.add(run)
        db.flush()

        executed: List[str] = []
        try:
            for step in defn.steps:
                if not self._should_run_step(step, event):
                    continue
                handler = self._actions.get(step.action)
                if not handler:
                    raise ValueError(f"Ação desconhecida: {step.action}")
                handler(db, step, event, run)
                executed.append(step.action)

            run.steps_executed = ", ".join(executed)
            run.status = WorkflowRunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            db.commit()
            logger.info(
                f"Workflow {defn.workflow_id} concluído "
                f"(event={event.event_type}, steps={executed})"
            )
            return run
        except Exception as exc:
            run.status = WorkflowRunStatus.FAILED
            run.error_message = str(exc)
            run.steps_executed = ", ".join(executed)
            run.completed_at = datetime.utcnow()
            db.commit()
            logger.error(f"Workflow {defn.workflow_id} falhou: {exc}")
            return run

    def _should_run_step(self, step: WorkflowStepDefinition, event: DomainEvent) -> bool:
        """
        Avalia condição ``when`` de um passo.

        Args:
            step: Passo do workflow.
            event: Evento de domínio.

        Returns:
            True se o passo deve executar.
        """
        if step.when == "always":
            return True
        if step.when == "deposit_paid":
            return bool(event.payload.get("agendamento_id") or event.payload.get("payment_id"))
        return True

    def _action_log(
        self,
        db: Session,
        step: WorkflowStepDefinition,
        event: DomainEvent,
        run: CoreWorkflowRun,
    ) -> None:
        """
        Ação built-in: registra mensagem no log.

        Args:
            db: Sessão (não usada).
            step: Passo com params.message.
            event: Evento disparador.
            run: Execução corrente.

        Returns:
            None
        """
        message = step.params.get("message", "workflow step")
        logger.info(f"[workflow:{run.workflow_id}] {message} (event={event.event_type})")

    def _action_notify_admin(
        self,
        db: Session,
        step: WorkflowStepDefinition,
        event: DomainEvent,
        run: CoreWorkflowRun,
    ) -> None:
        """
        Ação built-in: notifica admin sobre evento (log + futuro push/email).

        Args:
            db: Sessão SQLAlchemy.
            step: Passo com params.message.
            event: Evento disparador.
            run: Execução corrente.

        Returns:
            None
        """
        message = step.params.get(
            "message",
            f"Evento {event.event_type} requer atenção admin",
        )
        logger.info(
            f"[workflow:notify_admin] company={event.company_id} — {message}"
        )
        agendamento_id = event.payload.get("agendamento_id") or event.payload.get(
            "legacy_agendamento_id"
        )
        if agendamento_id:
            try:
                from app.services.notification_service import NotificationService

                NotificationService(db).notificar_reserva_aguardando_aprovacao(
                    int(agendamento_id)
                )
            except Exception as exc:
                logger.warning(f"notify_admin fallback log only: {exc}")


workflow_engine = WorkflowEngine()
