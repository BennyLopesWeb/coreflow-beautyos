"""
Service de configuração de agenda por dia.
"""
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional, Tuple

from app.models.agenda_dia import AgendaDia
from app.models.agendamento import Agendamento, STATUS_OCUPAM_VAGA
from app.models.cliente import Cliente
from app.models.tranca import Tranca
from app.schemas.agenda_dia import AgendaDiaCreate, SlotAgendaItem, AgendaDiaDetalheResponse


# Expediente padrão quando não há configuração para o dia
HORA_INICIO_PADRAO = 8
MINUTO_INICIO_PADRAO = 0
HORA_FIM_PADRAO = 18
MINUTO_FIM_PADRAO = 0


class AgendaDiaService:
    """
    Gerencia expediente por data e visão administrativa dos slots.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db

    def obter_ou_padrao(self, data_ref: date) -> Tuple[int, int, int, int, bool]:
        """
        Retorna horário de expediente para a data.

        Args:
            data_ref: Data consultada.

        Returns:
            Tupla (hora_inicio, minuto_inicio, hora_fim, minuto_fim, ativo).
        """
        config = self.db.query(AgendaDia).filter(AgendaDia.data == data_ref).first()
        if not config:
            return HORA_INICIO_PADRAO, MINUTO_INICIO_PADRAO, HORA_FIM_PADRAO, MINUTO_FIM_PADRAO, True
        return (
            config.hora_inicio,
            config.minuto_inicio,
            config.hora_fim,
            config.minuto_fim,
            config.ativo,
        )

    def salvar_config(self, data: AgendaDiaCreate) -> AgendaDia:
        """
        Cria ou atualiza configuração de um dia.

        Args:
            data: Dados de expediente.

        Returns:
            AgendaDia persistido.
        """
        config = self.db.query(AgendaDia).filter(AgendaDia.data == data.data).first()
        if config:
            config.hora_inicio = data.hora_inicio
            config.minuto_inicio = data.minuto_inicio
            config.hora_fim = data.hora_fim
            config.minuto_fim = data.minuto_fim
            config.ativo = data.ativo
        else:
            config = AgendaDia(**data.model_dump())
            self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def obter_visao_dia(
        self,
        data_ref: date,
        tranca_id: Optional[int] = None,
    ) -> AgendaDiaDetalheResponse:
        """
        Monta visão admin da agenda com slots e ocupação.

        Args:
            data_ref: Data da agenda.
            tranca_id: Trança de referência para duração (opcional).

        Returns:
            AgendaDiaDetalheResponse com slots marcados.
        """
        hi, mi, hf, mf, ativo = self.obter_ou_padrao(data_ref)
        base = datetime.combine(data_ref, datetime.min.time())

        slots: List[SlotAgendaItem] = []
        if ativo and tranca_id:
            from app.services.disponibilidade_service import DisponibilidadeService
            horarios = DisponibilidadeService(self.db).calcular_horarios_disponiveis(
                base.replace(hour=hi, minute=mi),
                tranca_id,
                service_image_id=None,
                ignorar_duracao_modelo=True,
            )
            agendamentos = (
                self.db.query(Agendamento, Cliente, Tranca)
                .join(Cliente, Agendamento.cliente_id == Cliente.id)
                .join(Tranca, Agendamento.tranca_id == Tranca.id)
                .filter(
                    Agendamento.data_hora >= base.replace(hour=hi, minute=mi),
                    Agendamento.data_hora < base.replace(hour=hf, minute=mf),
                    Agendamento.status.in_(STATUS_OCUPAM_VAGA),
                    Agendamento.deleted_at.is_(None),
                )
                .all()
            )
            ag_map = {
                ag.data_hora.replace(second=0, microsecond=0): (ag, cliente, tranca)
                for ag, cliente, tranca in agendamentos
            }
            for h in horarios:
                key = h.horario.replace(second=0, microsecond=0)
                ag_info = ag_map.get(key)
                slots.append(SlotAgendaItem(
                    horario=h.horario,
                    disponivel=h.disponivel,
                    agendamento_id=ag_info[0].id if ag_info else None,
                    cliente_nome=ag_info[1].nome if ag_info else None,
                    tranca_nome=ag_info[2].nome if ag_info else None,
                    status=ag_info[0].status.value if ag_info else None,
                ))
        else:
            current = base.replace(hour=hi, minute=mi, second=0, microsecond=0)
            fim = base.replace(hour=hf, minute=mf, second=0, microsecond=0)
            while current < fim:
                slots.append(SlotAgendaItem(horario=current, disponivel=not ativo))
                from datetime import timedelta
                current += timedelta(minutes=30)

        return AgendaDiaDetalheResponse(
            data=data_ref,
            hora_inicio=hi,
            minuto_inicio=mi,
            hora_fim=hf,
            minuto_fim=mf,
            ativo=ativo,
            slots=slots,
        )
