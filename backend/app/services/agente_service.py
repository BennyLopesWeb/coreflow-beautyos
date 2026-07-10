"""
Service do agente inteligente de automação CRM/atendimento.
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List

from app.models.agent_task import AgentTask, AgentTaskStatus, AgentTaskType
from app.models.agendamento import Agendamento, StatusAgendamento
from app.models.cliente import Cliente
from app.models.fila import Fila
from app.models.tranca import Tranca
from app.schemas.agente import AgenteExecutarResponse, AgentTaskResponse
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger

logger = get_logger("agente_service")


class AgenteService:
    """
    Agente inteligente que analisa o salão e gera/executa tarefas automatizadas.

    Simula ações de CRM: lembretes de pagamento, reativação de clientes,
    notificações de fila e follow-up pós-atendimento.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db

    def listar_tarefas(self, apenas_pendentes: bool = False) -> List[AgentTask]:
        """
        Lista tarefas do agente.

        Args:
            apenas_pendentes: Se True, retorna somente tarefas pendentes.

        Returns:
            Lista de AgentTask ordenada por criação decrescente.
        """
        query = self.db.query(AgentTask)
        if apenas_pendentes:
            query = query.filter(AgentTask.status == AgentTaskStatus.PENDENTE)
        return query.order_by(AgentTask.created_at.desc()).limit(50).all()

    def _tarefa_existe(
        self,
        tipo: AgentTaskType,
        referencia_id: int,
    ) -> bool:
        """
        Verifica se já existe tarefa pendente do mesmo tipo para a referência.

        Args:
            tipo: Tipo da tarefa.
            referencia_id: ID de referência (agendamento, cliente, etc.).

        Returns:
            True se já existir tarefa pendente equivalente.
        """
        return (
            self.db.query(AgentTask)
            .filter(
                AgentTask.tipo == tipo,
                AgentTask.referencia_id == referencia_id,
                AgentTask.status == AgentTaskStatus.PENDENTE,
            )
            .first()
            is not None
        )

    def analisar_e_criar_tarefas(self) -> int:
        """
        Analisa o banco e cria tarefas automatizadas pendentes.

        Returns:
            Quantidade de novas tarefas criadas.
        """
        criadas = 0
        hoje = date.today()
        limite_inativo = datetime.now() - timedelta(days=45)

        # Lembretes de pagamento pendente
        agendamentos_pendentes = self.db.query(Agendamento).filter(
            Agendamento.sinal_pago.is_(False),
            Agendamento.status == StatusAgendamento.PENDENTE,
            Agendamento.deleted_at.is_(None),
            Agendamento.data_hora >= datetime.now(),
        ).all()

        for ag in agendamentos_pendentes:
            if self._tarefa_existe(AgentTaskType.LEMBRETE_PAGAMENTO, ag.id):
                continue
            cliente = self.db.query(Cliente).filter(Cliente.id == ag.cliente_id).first()
            tranca = self.db.query(Tranca).filter(Tranca.id == ag.tranca_id).first()
            nome_cliente = cliente.nome if cliente else "Cliente"
            nome_tranca = tranca.nome if tranca else "serviço"
            tarefa = AgentTask(
                tipo=AgentTaskType.LEMBRETE_PAGAMENTO,
                titulo=f"Lembrete Pix — {nome_cliente}",
                descricao=(
                    f"Enviar lembrete de pagamento do sinal para {nome_cliente} "
                    f"({cliente.telefone if cliente else 'N/A'}) — {nome_tranca} "
                    f"em {ag.data_hora.strftime('%d/%m/%Y %H:%M')}."
                ),
                referencia_id=ag.id,
            )
            self.db.add(tarefa)
            criadas += 1

        # Reativar clientes inativos
        clientes = self.db.query(Cliente).filter(Cliente.deleted_at.is_(None)).all()
        for cliente in clientes:
            ultimo = (
                self.db.query(Agendamento)
                .filter(
                    Agendamento.cliente_id == cliente.id,
                    Agendamento.deleted_at.is_(None),
                    Agendamento.status != StatusAgendamento.CANCELADO,
                )
                .order_by(Agendamento.data_hora.desc())
                .first()
            )
            if ultimo and ultimo.data_hora >= limite_inativo:
                continue
            if self._tarefa_existe(AgentTaskType.REATIVAR_CLIENTE, cliente.id):
                continue
            tarefa = AgentTask(
                tipo=AgentTaskType.REATIVAR_CLIENTE,
                titulo=f"Reativar — {cliente.nome}",
                descricao=(
                    f"Cliente {cliente.nome} sem visita recente. "
                    f"Enviar mensagem promocional ou convite para agendar."
                ),
                referencia_id=cliente.id,
            )
            self.db.add(tarefa)
            criadas += 1

        # Notificar fila do dia
        fila_hoje = self.db.query(Fila).filter(
            Fila.data == hoje,
        ).order_by(Fila.posicao.asc()).all()

        for item in fila_hoje[:3]:
            if self._tarefa_existe(AgentTaskType.NOTIFICAR_FILA, item.id):
                continue
            ag = self.db.query(Agendamento).filter(Agendamento.id == item.agendamento_id).first()
            cliente = self.db.query(Cliente).filter(Cliente.id == ag.cliente_id).first() if ag else None
            tarefa = AgentTask(
                tipo=AgentTaskType.NOTIFICAR_FILA,
                titulo=f"Fila pos. {item.posicao} — {cliente.nome if cliente else 'Cliente'}",
                descricao=(
                    f"Notificar {cliente.nome if cliente else 'cliente'} "
                    f"sobre posição {item.posicao} na fila de hoje."
                ),
                referencia_id=item.id,
            )
            self.db.add(tarefa)
            criadas += 1

        self.db.commit()
        logger.info(f"Agente criou {criadas} novas tarefas")
        return criadas

    def executar_tarefa(self, task_id: int) -> AgentTask:
        """
        Executa uma tarefa pendente do agente (simulação de automação).

        Args:
            task_id: ID da tarefa.

        Returns:
            AgentTask atualizada com status executada.

        Raises:
            NotFoundError: Se tarefa não existir.
        """
        tarefa = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not tarefa:
            raise NotFoundError("Tarefa não encontrada")

        if tarefa.status != AgentTaskStatus.PENDENTE:
            return tarefa

        resultado = self._simular_execucao(tarefa)
        tarefa.status = AgentTaskStatus.EXECUTADA
        tarefa.resultado = resultado
        tarefa.executed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(tarefa)
        return tarefa

    def _simular_execucao(self, tarefa: AgentTask) -> str:
        """
        Simula a execução de uma tarefa (WhatsApp/e-mail mock).

        Args:
            tarefa: Tarefa a executar.

        Returns:
            Mensagem de resultado da execução simulada.
        """
        acoes = {
            AgentTaskType.LEMBRETE_PAGAMENTO: "WhatsApp: lembrete de Pix enviado ao cliente.",
            AgentTaskType.REATIVAR_CLIENTE: "WhatsApp: mensagem de reativação enviada.",
            AgentTaskType.NOTIFICAR_FILA: "WhatsApp: cliente notificado sobre posição na fila.",
            AgentTaskType.CONFIRMAR_AGENDAMENTO: "Agendamento confirmado automaticamente.",
            AgentTaskType.FOLLOW_UP: "WhatsApp: pesquisa de satisfação enviada.",
        }
        msg = acoes.get(tarefa.tipo, "Tarefa executada com sucesso.")
        logger.info(f"Tarefa {tarefa.id} executada: {msg}")
        return msg

    def executar_automacoes(self) -> AgenteExecutarResponse:
        """
        Analisa o salão, cria tarefas e executa as pendentes mais urgentes.

        Returns:
            AgenteExecutarResponse com contadores e lista de tarefas recentes.
        """
        criadas = self.analisar_e_criar_tarefas()
        pendentes = self.listar_tarefas(apenas_pendentes=True)
        executadas = 0

        for tarefa in pendentes[:5]:
            self.executar_tarefa(tarefa.id)
            executadas += 1

        tarefas = self.listar_tarefas()
        return AgenteExecutarResponse(
            tarefas_criadas=criadas,
            tarefas_executadas=executadas,
            mensagem=(
                f"Agente analisou o salão: {criadas} tarefa(s) criada(s), "
                f"{executadas} executada(s) automaticamente."
            ),
            tarefas=[AgentTaskResponse.model_validate(t) for t in tarefas],
        )
