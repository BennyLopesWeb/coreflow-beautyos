"""
Service do agente inteligente de automação CRM/atendimento.

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida (DROP físico — ADR-024 sunset /
    RFC-003 M11+). ``analisar_e_criar_tarefas`` agora usa ``CoreBooking``
    (fonte da verdade desde R3-F2/R4-F4) como equivalente para "lembrete
    de pagamento pendente" e "última visita do cliente" — ver
    ``docs/sprints/R4-F8.md``.
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List

from app.models.agent_task import AgentTask, AgentTaskStatus, AgentTaskType
from app.models.agendamento import ReservationStatus
from app.models.cliente import Cliente
from app.models.fila import Fila
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

        .. deprecated:: 2.11.0-r4-f8
            "Lembretes de pagamento pendente" e "última visita do cliente"
            usavam ``Agendamento`` legado; a tabela foi removida (DROP
            físico — ADR-024 sunset / RFC-003 M11+). Ambos os blocos foram
            reescritos para usar ``CoreBooking`` (fonte da verdade desde
            R3-F2/R4-F4) como equivalente direto.

        Returns:
            Quantidade de novas tarefas criadas.
        """
        from app.modules.booking.domain.models import CoreBooking

        criadas = 0
        hoje = date.today()
        limite_inativo = datetime.now() - timedelta(days=45)

        # Lembretes de pagamento pendente (equivalente CoreBooking — R4-F8)
        bookings_pendentes = self.db.query(CoreBooking).filter(
            CoreBooking.deposit_paid.is_(False),
            CoreBooking.status == ReservationStatus.PENDING_PAYMENT,
            CoreBooking.deleted_at.is_(None),
            CoreBooking.scheduled_at >= datetime.now(),
        ).all()

        for booking in bookings_pendentes:
            if self._tarefa_existe(AgentTaskType.LEMBRETE_PAGAMENTO, booking.id):
                continue
            cliente = self.db.query(Cliente).filter(Cliente.id == booking.customer_id).first()
            nome_cliente = cliente.nome if cliente else "Cliente"
            nome_servico = booking.offering.name if booking.offering else "serviço"
            tarefa = AgentTask(
                tipo=AgentTaskType.LEMBRETE_PAGAMENTO,
                titulo=f"Lembrete Pix — {nome_cliente}",
                descricao=(
                    f"Enviar lembrete de pagamento do sinal para {nome_cliente} "
                    f"({cliente.telefone if cliente else 'N/A'}) — {nome_servico} "
                    f"em {booking.scheduled_at.strftime('%d/%m/%Y %H:%M')}."
                ),
                referencia_id=booking.id,
            )
            self.db.add(tarefa)
            criadas += 1

        # Reativar clientes inativos (última visita via CoreBooking — R4-F8)
        clientes = self.db.query(Cliente).filter(Cliente.deleted_at.is_(None)).all()
        for cliente in clientes:
            ultimo = (
                self.db.query(CoreBooking)
                .filter(
                    CoreBooking.customer_id == cliente.id,
                    CoreBooking.deleted_at.is_(None),
                    CoreBooking.status != ReservationStatus.CANCELLED,
                )
                .order_by(CoreBooking.scheduled_at.desc())
                .first()
            )
            if ultimo and ultimo.scheduled_at >= limite_inativo:
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
            cliente = self.db.query(Cliente).filter(Cliente.id == item.cliente_id).first()
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
