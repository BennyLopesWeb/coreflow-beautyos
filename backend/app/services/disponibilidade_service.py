"""
Service de Disponibilidade
Lógica de negócio para cálculo de horários disponíveis.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional, Set

from app.models.agendamento import Agendamento, ReservationStatus, STATUS_OCUPAM_VAGA
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.agendamento import HorarioDisponivel
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.core.logging_config import get_logger
from app.utils.service_image_precos import resolver_precos_imagem
from app.services.agenda_dia_service import AgendaDiaService

logger = get_logger("disponibilidade_service")

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

        R4-F6: cobre tanto ``Agendamento`` legado (histórico, mantido só
        para leitura desde R4-F4) quanto ``CoreBooking`` (fonte primária de
        ocupação desde R4-F4) — bookings core-only pendentes sem sinal
        pago também expiram, cancelados via ``CancelBookingHandler`` (path
        core, sem depender de criar/cancelar linha em ``Agendamento``).

        Returns:
            Quantidade total de reservas expiradas (legado + core).
        """
        count = self._expirar_agendamentos_pendentes()
        count += self._expirar_core_bookings_pendentes()
        return count

    def _expirar_agendamentos_pendentes(self) -> int:
        """
        Cancela ``Agendamento`` legado pendente sem sinal pago (histórico).

        Returns:
            Quantidade de agendamentos legados expirados.
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

    def _expirar_core_bookings_pendentes(self) -> int:
        """
        Cancela ``CoreBooking`` pendente sem sinal pago (R4-F6).

        Equivalente ao expirar de ``Agendamento`` legado, mas para bookings
        core-only: usa ``CancelBookingHandler`` (mesma policy usada por
        ``POST /v1/bookings/{id}/cancel``) em vez de manipular o ORM
        diretamente — garante que o evento ``booking.cancelled`` seja
        publicado e que a policy de cancelamento (sempre permitida para
        ``PENDING``) seja respeitada. Falhas isoladas em um booking não
        interrompem a expiração dos demais (best-effort, logado).

        Returns:
            Quantidade de bookings core expirados.
        """
        from app.modules.booking.domain.models import CoreBooking
        from app.modules.booking.application.commands.cancel_booking import (
            CancelBookingCommand,
            CancelBookingHandler,
        )

        limite = datetime.now() - timedelta(hours=EXPIRACAO_PENDENTE_HORAS)
        pendentes = self.db.query(CoreBooking).filter(
            CoreBooking.status == ReservationStatus.PENDING_PAYMENT,
            CoreBooking.deposit_paid.is_(False),
            CoreBooking.created_at < limite,
            CoreBooking.deleted_at.is_(None),
        ).all()

        handler = CancelBookingHandler(self.db)
        count = 0
        for booking in pendentes:
            try:
                handler.execute(
                    CancelBookingCommand(
                        booking_id=booking.id,
                        company_id=booking.company_id,
                        reason="expirado",
                    )
                )
                count += 1
            except Exception:
                logger.warning(
                    "Falha ao expirar CoreBooking id=%s", booking.id, exc_info=True
                )
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

        R4-F7 (cutover de disponibilidade core-only completo / ADR-024 /
        RFC-003 M11): ``core_bookings`` é a **única** fonte de ocupação —
        a leitura de compatibilidade sobre ``Agendamento`` legado (mantida
        desde R4-F4/R4-F6 para reservas históricas ativas) foi removida
        nesta release. Nenhum caminho de escrita de produção insere linha
        em ``agendamentos`` desde R3-F2/R4-F3 (ver
        ``AgendamentoService.criar_agendamento``, sempre
        ``BusinessRuleError``); reservas legado históricas que ainda
        estejam com status ativo (criadas antes da migração para
        ``core_bookings``) não bloqueiam mais slots aqui — débito residual
        aceito e documentado no gate R4-F7 (tabela ``agendamentos``
        permanece somente leitura para relatórios/sync, sem DROP físico
        até R4-F8).

        Args:
            data_inicio: Início do expediente.
            data_fim: Fim do expediente.

        Returns:
            Set de datetimes (início de cada slot de 30 min ocupado) —
            exclusivamente a partir de ``core_bookings`` ativos.
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
