"""
Service de Schedule — blocos de agenda vinculados a reservas.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional

from app.models.schedule import Schedule, ScheduleStatus
from app.models.agendamento import Agendamento, STATUS_OCUPAM_VAGA
from app.core.exceptions import BusinessRuleError, NotFoundError


class ScheduleService:
    """
    Gerencia ocupação de horários na agenda via tabela schedules.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db

    def _duracao_minutos(self, ag: Agendamento) -> int:
        """
        Obtém duração do atendimento a partir do modelo.

        Args:
            ag: Reserva.

        Returns:
            Duração em minutos.
        """
        if ag.service_image and ag.service_image.duracao_minutos:
            return int(ag.service_image.duracao_minutos)
        return 60

    def tem_conflito(
        self,
        inicio: datetime,
        fim: datetime,
        excluir_agendamento_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica sobreposição com schedules ativos.

        Args:
            inicio: Início do slot.
            fim: Fim do slot.
            excluir_agendamento_id: Reserva a ignorar.

        Returns:
            True se houver conflito.
        """
        query = self.db.query(Schedule).filter(
            Schedule.status == ScheduleStatus.SCHEDULED,
            Schedule.inicio < fim,
            Schedule.fim > inicio,
        )
        if excluir_agendamento_id:
            query = query.filter(Schedule.agendamento_id != excluir_agendamento_id)
        return query.first() is not None

    def criar_para_reserva(self, ag: Agendamento) -> Schedule:
        """
        Cria schedule ao aprovar reserva.

        .. deprecated:: 2.9.0-r4-f6
            Sem call-site ativo em produção desde R4-F6 (ADR-024 sunset) —
            ``ReservationService.aceitar_reagendamento`` (único caminho de
            escrita restante) parou de chamar este método; bookings novos
            são sempre core-only (``CoreBooking``), sem ``Schedule``
            associado. Método mantido (não removido — model ``Schedule``
            preservado, DROP físico adiado para R4-F8) apenas por
            compatibilidade de referência/import e para dados legado que
            ainda dependam dele fora do fluxo HTTP padrão. R4-F7 removeu a
            FK física de ``Schedule.agendamento_id`` para ``agendamentos.id``
            (coluna nullable, sem constraint) — este método continua
            funcional (não levanta ``BusinessRuleError``) caso algum
            consumidor legado ainda o invoque diretamente, mas nenhum path
            HTTP ativo o faz.

        Args:
            ag: Reserva aprovada.

        Returns:
            Schedule criado.

        Raises:
            BusinessRuleError: Se houver conflito de horário.
        """
        inicio = ag.horario_aprovado or ag.data_hora
        duracao = self._duracao_minutos(ag)
        fim = inicio + timedelta(minutes=duracao)

        if self.tem_conflito(inicio, fim, ag.id):
            raise BusinessRuleError(
                f"Horário {inicio.strftime('%H:%M')}–{fim.strftime('%H:%M')} já ocupado"
            )

        existente = (
            self.db.query(Schedule).filter(Schedule.agendamento_id == ag.id).first()
        )
        if existente:
            existente.inicio = inicio
            existente.fim = fim
            existente.data = inicio.date()
            existente.status = ScheduleStatus.SCHEDULED
            self.db.commit()
            self.db.refresh(existente)
            return existente

        sch = Schedule(
            agendamento_id=ag.id,
            data=inicio.date(),
            inicio=inicio,
            fim=fim,
            status=ScheduleStatus.SCHEDULED,
        )
        self.db.add(sch)
        self.db.commit()
        self.db.refresh(sch)
        return sch

    def cancelar(self, agendamento_id: int) -> None:
        """
        Cancela schedule de uma reserva.

        Args:
            agendamento_id: ID da reserva.
        """
        sch = (
            self.db.query(Schedule)
            .filter(Schedule.agendamento_id == agendamento_id)
            .first()
        )
        if sch:
            sch.status = ScheduleStatus.CANCELLED
            self.db.commit()

    def concluir(self, agendamento_id: int) -> None:
        """
        Marca schedule como concluído.

        Args:
            agendamento_id: ID da reserva.
        """
        sch = (
            self.db.query(Schedule)
            .filter(Schedule.agendamento_id == agendamento_id)
            .first()
        )
        if sch:
            sch.status = ScheduleStatus.COMPLETED
            self.db.commit()

    def listar_por_data(self, data_ref: date) -> List[Schedule]:
        """
        Lista schedules de um dia.

        Args:
            data_ref: Data consultada.

        Returns:
            Lista de Schedule.
        """
        return (
            self.db.query(Schedule)
            .filter(Schedule.data == data_ref, Schedule.status == ScheduleStatus.SCHEDULED)
            .order_by(Schedule.inicio)
            .all()
        )
