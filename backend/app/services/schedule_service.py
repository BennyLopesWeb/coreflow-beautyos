"""
Service de Schedule — blocos de agenda vinculados a reservas.

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida (DROP físico — ADR-024 sunset /
    RFC-003 M11+). ``criar_para_reserva``/``_duracao_minutos`` (que
    recebiam um ``Agendamento`` como argumento) foram removidos por já
    não terem call-site ativo desde R4-F6. Os métodos restantes
    (``tem_conflito``, ``cancelar``, ``concluir``, ``listar_por_data``)
    operam apenas sobre a tabela ``schedules`` e a coluna
    ``Schedule.agendamento_id`` (inteiro simples, sem FK desde R4-F7) —
    continuam funcionais e são usados por ``SchedulingPort`` (ACL) para
    detectar conflito de horário em bookings core-only.
"""
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional

from app.models.schedule import Schedule, ScheduleStatus


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
