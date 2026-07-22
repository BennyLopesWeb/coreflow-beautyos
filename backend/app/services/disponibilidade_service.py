"""
Service de Disponibilidade
Lógica de negócio para cálculo de horários disponíveis.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional, Set

from app.models.agendamento import Agendamento, STATUS_OCUPAM_VAGA
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.agendamento import HorarioDisponivel
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.utils.service_image_precos import resolver_precos_imagem
from app.services.agenda_dia_service import AgendaDiaService

# Duração padrão quando consulta admin sem modelo (slot de 30 min)
DURACAO_PADRAO_MIN = 30

# Reservas sem pagamento expiram após este prazo
EXPIRACAO_PENDENTE_HORAS = 2


class DisponibilidadeService:
    """
    Service para cálculo de disponibilidade de horários.
    Considera duração do modelo, expediente do dia e capacidade única do salão.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db
        self.agenda_dia = AgendaDiaService(db)

    def expirar_reservas_pendentes(self) -> int:
        """
        Cancela reservas pendentes sem pagamento após prazo de expiração.

        Returns:
            Quantidade de reservas expiradas.
        """
        from app.models.agendamento import StatusAgendamento
        from app.services.agendamento_service import AgendamentoService

        limite = datetime.now() - timedelta(hours=EXPIRACAO_PENDENTE_HORAS)
        pendentes = self.db.query(Agendamento).filter(
            Agendamento.status == StatusAgendamento.PENDENTE,
            Agendamento.sinal_pago.is_(False),
            Agendamento.created_at < limite,
            Agendamento.deleted_at.is_(None),
        ).all()

        svc = AgendamentoService(self.db)
        count = 0
        for ag in pendentes:
            svc.cancelar_agendamento(ag.id, liberar_vaga=True, motivo="expirado")
            count += 1
        return count

    def _duracao_minutos(
        self,
        tranca: Tranca,
        service_image_id: Optional[int] = None,
        ignorar_duracao_modelo: bool = False,
    ) -> int:
        """
        Resolve duração do atendimento.

        Args:
            tranca: Categoria da trança.
            service_image_id: ID do modelo selecionado.
            ignorar_duracao_modelo: Usa duração padrão (visão admin).

        Returns:
            Duração em minutos.

        Raises:
            BusinessRuleError: Se modelo obrigatório não informado.
        """
        if ignorar_duracao_modelo or not service_image_id:
            if ignorar_duracao_modelo:
                return DURACAO_PADRAO_MIN
            raise BusinessRuleError("Selecione um modelo para consultar horários")
        img = (
            self.db.query(ServiceImage)
            .filter(ServiceImage.id == service_image_id, ServiceImage.deleted_at.is_(None))
            .first()
        )
        if not img or img.service_id != tranca.id:
            raise BusinessRuleError("Modelo inválido para esta categoria")
        try:
            return int(resolver_precos_imagem(img)["duracao_minutos"])
        except ValueError as e:
            raise BusinessRuleError(str(e))

    def _duracao_agendamento(self, agendamento: Agendamento) -> int:
        """
        Obtém duração de um agendamento existente.

        Args:
            agendamento: Agendamento persistido.

        Returns:
            Duração em minutos.
        """
        tranca = self.db.query(Tranca).filter(Tranca.id == agendamento.tranca_id).first()
        if not tranca:
            return DURACAO_PADRAO_MIN
        if agendamento.service_image_id:
            try:
                return self._duracao_minutos(tranca, agendamento.service_image_id)
            except BusinessRuleError:
                pass
        return DURACAO_PADRAO_MIN

    def _duracao_core_booking(self, booking) -> int:
        """
        Obtém duração de um ``CoreBooking`` existente via ``core_offerings``.

        Args:
            booking: Instância de ``CoreBooking`` persistida.

        Returns:
            Duração em minutos (``DURACAO_PADRAO_MIN`` se offering sem duração).
        """
        offering = booking.offering
        if offering and offering.duration_minutes:
            return int(offering.duration_minutes)
        return DURACAO_PADRAO_MIN

    def _slots_ocupados(self, data_inicio: datetime, data_fim: datetime) -> Set[datetime]:
        """
        Calcula conjunto de slots de 30 min ocupados no intervalo (capacidade única).

        R4-F4 (hard sunset / ADR-024 / RFC-003 M8): ``core_bookings`` é a
        fonte primária de ocupação — nenhum novo booking gera linha em
        ``agendamentos`` desde R3-F2/R4-F3. A consulta a ``Agendamento``
        é mantida apenas para cobrir reservas históricas (criadas antes da
        migração) que ainda estejam com status ativo.

        Args:
            data_inicio: Início do expediente.
            data_fim: Fim do expediente.

        Returns:
            Set de datetimes (início de cada slot de 30 min ocupado), união
            de ``core_bookings`` ativos (primário) e ``agendamentos``
            históricos ativos (legado, somente leitura).
        """
        from app.modules.booking.domain.models import CoreBooking

        ocupados: Set[datetime] = set()

        core_bookings = self.db.query(CoreBooking).filter(
            CoreBooking.scheduled_at >= data_inicio,
            CoreBooking.scheduled_at < data_fim,
            CoreBooking.status.in_(STATUS_OCUPAM_VAGA),
            CoreBooking.deleted_at.is_(None),
        ).all()
        for booking in core_bookings:
            duracao = self._duracao_core_booking(booking)
            inicio = booking.scheduled_at.replace(second=0, microsecond=0)
            for i in range(0, duracao, 30):
                ocupados.add(inicio + timedelta(minutes=i))

        agendamentos = self.db.query(Agendamento).filter(
            Agendamento.data_hora >= data_inicio,
            Agendamento.data_hora < data_fim,
            Agendamento.status.in_(STATUS_OCUPAM_VAGA),
            Agendamento.deleted_at.is_(None),
        ).all()
        for ag in agendamentos:
            duracao = self._duracao_agendamento(ag)
            inicio = ag.data_hora.replace(second=0, microsecond=0)
            for i in range(0, duracao, 30):
                ocupados.add(inicio + timedelta(minutes=i))

        return ocupados

    def calcular_horarios_disponiveis(
        self,
        data: datetime,
        tranca_id: int,
        service_image_id: Optional[int] = None,
        ignorar_duracao_modelo: bool = False,
    ) -> List[HorarioDisponivel]:
        """
        Calcula horários disponíveis para uma data e trança.

        Args:
            data: Data base da consulta.
            tranca_id: ID da categoria.
            service_image_id: ID do modelo (duração individual).
            ignorar_duracao_modelo: Usa slot de 30 min (admin).

        Returns:
            Lista de slots com flag disponível/indisponível.
        """
        self.expirar_reservas_pendentes()

        tranca = self.db.query(Tranca).filter(Tranca.id == tranca_id).first()
        if not tranca:
            raise NotFoundError("Trança", str(tranca_id))
        if not tranca.ativo:
            raise BusinessRuleError("Trança não está ativa")

        duracao_consulta = self._duracao_minutos(
            tranca, service_image_id, ignorar_duracao_modelo
        )

        data_date = data.date()
        hi, mi, hf, mf, ativo = self.agenda_dia.obter_ou_padrao(data_date)
        if not ativo:
            return []

        data_inicio = data.replace(hour=hi, minute=mi, second=0, microsecond=0)
        data_fim = data.replace(hour=hf, minute=mf, second=0, microsecond=0)
        horarios_ocupados = self._slots_ocupados(data_inicio, data_fim)

        horarios_disponiveis: List[HorarioDisponivel] = []
        current = data_inicio
        agora = datetime.now()

        while current < data_fim:
            if current < agora:
                horarios_disponiveis.append(HorarioDisponivel(horario=current, disponivel=False))
            else:
                conflito = False
                for i in range(0, duracao_consulta, 30):
                    slot = current + timedelta(minutes=i)
                    slot_rounded = slot.replace(second=0, microsecond=0)
                    if slot_rounded in horarios_ocupados or slot >= data_fim:
                        conflito = True
                        break
                horarios_disponiveis.append(HorarioDisponivel(horario=current, disponivel=not conflito))
            current += timedelta(minutes=30)

        return horarios_disponiveis

    def tem_horarios_disponiveis(
        self,
        data: datetime,
        tranca_id: int,
        service_image_id: int,
    ) -> bool:
        """
        Verifica se existe ao menos um slot livre na data.

        Args:
            data: Data consultada.
            tranca_id: ID da categoria.
            service_image_id: ID do modelo.

        Returns:
            True se houver slot disponível.
        """
        horarios = self.calcular_horarios_disponiveis(data, tranca_id, service_image_id)
        return any(h.disponivel for h in horarios)
