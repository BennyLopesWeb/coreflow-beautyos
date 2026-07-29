"""
Service de Disponibilidade
Lógica de negócio para cálculo de horários disponíveis.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Set, FrozenSet

from app.models.agendamento import ReservationStatus, StatusPagamento, STATUS_OCUPAM_VAGA
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.agendamento import HorarioDisponivel
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.core.logging_config import get_logger
from app.utils.service_image_precos import resolver_precos_imagem
from app.services.agenda_dia_service import AgendaDiaService
from app.modules.booking.domain.policy.cancel_window import ensure_utc

logger = get_logger("disponibilidade_service")

# Duração padrão quando consulta admin sem modelo (slot de 30 min)
DURACAO_PADRAO_MIN = 30

# Status ORM que o ExpireBookingHandler consegue expirar com segurança
# (mapeiam para lifecycle PENDING). Alias ambíguo "pending" NÃO entra aqui.
_EXPIRATION_SAFE_ORM_STATUSES: FrozenSet[ReservationStatus] = frozenset(
    {
        ReservationStatus.PENDING_PAYMENT,
        ReservationStatus.PENDING_APPROVAL,
        ReservationStatus.WAITING_TIME_CONFIRMATION,
        ReservationStatus.PENDENTE,
    }
)
_EXPIRATION_SAFE_STATUS_VALUES: FrozenSet[str] = frozenset(
    s.value for s in _EXPIRATION_SAFE_ORM_STATUSES
)

# payment_status do booking que evidenciam dinheiro recebido (FIX-EXPIRATION-02C).
_PROTECTED_BOOKING_PAYMENT_STATUS_VALUES: FrozenSet[str] = frozenset(
    {
        StatusPagamento.PARTIALLY_PAID.value,
        StatusPagamento.CONFIRMED.value,
        StatusPagamento.PAID.value,
    }
)


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

        .. deprecated:: 2.11.0-r4-f8
            Cobria historicamente tanto ``Agendamento`` legado quanto
            ``CoreBooking``. A tabela ``agendamentos`` foi removida
            fisicamente (DROP — ADR-024 sunset / RFC-003 M11+); nenhum
            caminho de escrita cria reservas legado desde R3-F2/R4-F3/R4-F4,
            então não há mais nada a expirar por esse lado. Cobre apenas
            ``CoreBooking`` (fonte primária de ocupação), cancelado via
            ``CancelBookingHandler``.

        Returns:
            Quantidade de reservas core expiradas.
        """
        return self._expirar_core_bookings_pendentes()

    @staticmethod
    def _expiration_status_is_eligible(
        booking_status: ReservationStatus,
        eligible_statuses,
    ) -> bool:
        """
        Verifica se o status ORM do booking está na lista elegível da política.

        Só considera aliases com mapeamento seguro para status PENDING-like.
        Entradas desconhecidas ou ambíguas (ex.: ``pending``) são ignoradas
        sem expandir o conjunto — fail-closed por booking.

        Args:
            booking_status: Status ORM atual do ``CoreBooking``.
            eligible_statuses: Iterável de strings da política
                (``expiration.eligible_statuses``).

        Returns:
            ``True`` se o status do booking é seguro para expire e está
            listado de forma explícita na política; ``False`` caso contrário.
        """
        if booking_status not in _EXPIRATION_SAFE_ORM_STATUSES:
            return False
        allowed_safe = {
            value
            for value in (eligible_statuses or ())
            if value in _EXPIRATION_SAFE_STATUS_VALUES
        }
        return booking_status.value in allowed_safe

    @staticmethod
    def _expiration_reference_timestamp(
        booking,
        reference: str,
    ) -> Optional[datetime]:
        """
        Resolve o timestamp de referência temporal da política de expiração.

        Args:
            booking: Instância ``CoreBooking`` candidata.
            reference: Valor de ``expiration.reference``
                (``created_at`` ou ``scheduled_at``).

        Returns:
            Datetime aware em UTC do campo escolhido, ou ``None`` se a
            referência for desconhecida ou o timestamp estiver ausente
            (fail-closed — booking não expira neste ciclo).
        """
        if reference == "created_at":
            raw = booking.created_at
        elif reference == "scheduled_at":
            raw = booking.scheduled_at
        else:
            logger.warning(
                "CoreBooking id=%s reference de expiração desconhecida=%r — "
                "ignorado (fail-closed)",
                getattr(booking, "id", None),
                reference,
            )
            return None
        if raw is None:
            return None
        return ensure_utc(raw)

    def _booking_payment_status_value(self, booking) -> Optional[str]:
        """
        Normaliza ``payment_status`` do booking para string canônica.

        Args:
            booking: Instância ``CoreBooking`` (ou stub de teste).

        Returns:
            Valor string do status, ou ``None`` se ausente.
        """
        status = getattr(booking, "payment_status", None)
        if status is None:
            return None
        if hasattr(status, "value"):
            return str(status.value)
        return str(status)

    def _load_booking_ids_with_active_payment_rows(
        self, booking_ids: List[int]
    ) -> Set[int]:
        """
        Identifica bookings com linha financeira ativa em ``payments`` ou
        ``core_payments`` (FIX-EXPIRATION-02C).

        Considera ativo apenas status comprovadamente recebidos
        (``paid``/``pago``/``processando`` em ``Payment``; ``paid`` em
        ``CorePayment``). Ignora pending/failed/refunded/cancelado e
        soft-deleted. Em erro de consulta, propaga a exceção para o
        chamador aplicar fail-closed.

        Args:
            booking_ids: IDs de ``core_bookings`` a inspecionar.

        Returns:
            Conjunto de ``booking_id`` com evidência financeira ativa.

        Raises:
            Exception: Qualquer falha de consulta ao banco.
        """
        from app.models.payment import Payment, PaymentStatus
        from app.modules.payments.models import CorePayment, CorePaymentStatus

        if not booking_ids:
            return set()

        active_payment_statuses = (
            PaymentStatus.PAID,
            PaymentStatus.PAGO,
            # Fail-closed: processamento em andamento é evidência ambígua.
            PaymentStatus.PROCESSANDO,
        )
        protected: Set[int] = set()

        payment_rows = (
            self.db.query(Payment.booking_id)
            .filter(
                Payment.booking_id.in_(booking_ids),
                Payment.deleted_at.is_(None),
                Payment.status.in_(active_payment_statuses),
            )
            .distinct()
            .all()
        )
        for (booking_id,) in payment_rows:
            if booking_id is not None:
                protected.add(int(booking_id))

        core_rows = (
            self.db.query(CorePayment.booking_id)
            .filter(
                CorePayment.booking_id.in_(booking_ids),
                CorePayment.deleted_at.is_(None),
                CorePayment.status == CorePaymentStatus.PAID,
            )
            .distinct()
            .all()
        )
        for (booking_id,) in core_rows:
            if booking_id is not None:
                protected.add(int(booking_id))

        return protected

    def _has_any_protected_payment(
        self,
        booking,
        *,
        payment_row_protected_ids: Optional[Set[int]] = None,
    ) -> bool:
        """
        Indica se o booking possui qualquer evidência de pagamento que
        bloqueia expiração automática (FIX-EXPIRATION-02C).

        Fontes (fail-closed):
        - ``deposit_paid=True``;
        - ``payment_status`` em partially_paid/confirmed/paid;
        - linha ativa em ``payments`` / ``core_payments`` (quando o
          conjunto pré-carregado estiver disponível, ou via consulta).

        Não altera dados financeiros. Erro de consulta → protegido.

        Args:
            booking: Candidato à expiração.
            payment_row_protected_ids: IDs com linhas ativas pré-carregadas
                neste lote. Se ``None``, consulta sob demanda.

        Returns:
            ``True`` se a reserva deve ser preservada (não expirar).
        """
        company_id = getattr(booking, "company_id", None)
        booking_id = getattr(booking, "id", None)

        try:
            if bool(getattr(booking, "deposit_paid", False)):
                return True

            pay_status = self._booking_payment_status_value(booking)
            if pay_status in _PROTECTED_BOOKING_PAYMENT_STATUS_VALUES:
                return True

            if booking_id is None:
                # Sem id: não dá para cruzar financeiro com segurança.
                logger.warning(
                    "Expiração: booking sem id — tratado como protegido "
                    "(fail-closed) company_id=%s",
                    company_id,
                )
                return True

            if payment_row_protected_ids is not None:
                return int(booking_id) in payment_row_protected_ids

            return int(booking_id) in self._load_booking_ids_with_active_payment_rows(
                [int(booking_id)]
            )
        except Exception:
            logger.warning(
                "Falha ao avaliar evidência financeira booking_id=%s "
                "company_id=%s — expiração ignorada (fail-closed)",
                booking_id,
                company_id,
                exc_info=True,
            )
            return True

    def _expirar_core_bookings_pendentes(self) -> int:
        """
        Expira ``CoreBooking`` elegível sem evidência de pagamento
        (FIX-EXPIRATION-02A/02B/02C).

        Candidatos SQL: status PENDING-like seguros, não soft-deleted.
        Por tenant: ``enabled``, ``after_hours``, ``reference``,
        ``eligible_statuses``. Antes do handler, aplica proteção financeira
        via ``_has_any_protected_payment`` (deposit_paid, payment_status,
        Payment/CorePayment).

        Comparação exclusiva: ``reference_ts < now - after_hours``.

        FIX-EXPIRATION-02C: ``require_unpaid_deposit=false`` é lido, mas
        **não** amplia elegibilidade — qualquer evidência de pagamento
        bloqueia até existir ``FIX-RESCHEDULE-*``. ``touch_payment_status``
        permanece sem efeito. ``payment_status`` é lido só para proteção;
        nunca alterado aqui.

        Falhas isoladas (resolve, booking sem tenant, handler, financeiro)
        não interrompem o lote — best-effort com log.

        Returns:
            Quantidade de bookings core expirados neste ciclo.
        """
        from app.modules.booking.application.commands.expire_booking import (
            ExpireBookingCommand,
            ExpireBookingHandler,
        )
        from app.modules.booking.domain.models import CoreBooking
        from app.modules.booking.domain.policy.resolver import BookingPolicyResolver

        # Pré-filtro: só status com caminho seguro até ExpireBookingHandler.
        # Proteção financeira (deposit/payment_status/Payment/CorePayment)
        # é aplicada por booking antes do handler — fail-closed.
        pendentes = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.status.in_(list(_EXPIRATION_SAFE_ORM_STATUSES)),
                CoreBooking.deleted_at.is_(None),
            )
            .all()
        )

        booking_ids = [
            int(b.id) for b in pendentes if getattr(b, "id", None) is not None
        ]
        try:
            payment_row_protected_ids = self._load_booking_ids_with_active_payment_rows(
                booking_ids
            )
        except Exception:
            logger.warning(
                "Falha ao pré-carregar evidências financeiras do lote de "
                "expiração — todos os candidatos tratados como protegidos "
                "(fail-closed)",
                exc_info=True,
            )
            payment_row_protected_ids = set(booking_ids)

        handler = ExpireBookingHandler(self.db)
        resolver = BookingPolicyResolver(self.db)
        # Cache por company_id neste lote (nunca reutilizar política entre tenants).
        policy_by_company: Dict[int, object] = {}
        resolve_failed: Set[int] = set()
        # Naive local (como created_at/scheduled_at tipicamente persistidos) → UTC
        # via ensure_utc, preservando a semântica de comparação do FIX-EXPIRATION-01.
        now = ensure_utc(datetime.now())
        count = 0

        for booking in pendentes:
            try:
                company_id = booking.company_id
                if company_id is None or not isinstance(company_id, int) or company_id <= 0:
                    logger.warning(
                        "CoreBooking id=%s sem company_id válido — expiração "
                        "ignorada (fail-closed)",
                        booking.id,
                    )
                    continue

                if company_id in resolve_failed:
                    continue

                if company_id not in policy_by_company:
                    try:
                        policy_by_company[company_id] = resolver.resolve(company_id)
                    except Exception:
                        resolve_failed.add(company_id)
                        logger.warning(
                            "Falha ao resolver política de expiração "
                            "company_id=%s — bookings do tenant ignorados neste lote",
                            company_id,
                            exc_info=True,
                        )
                        continue

                policy = policy_by_company[company_id]
                expiration = policy.expiration
                if not expiration.enabled:
                    continue

                # FIX-EXPIRATION-02C — require_unpaid_deposit=false NÃO amplia
                # elegibilidade até FIX-RESCHEDULE-*. Qualquer evidência de
                # pagamento continua bloqueando a expiração.
                if expiration.require_unpaid_deposit is False:
                    pass

                if self._has_any_protected_payment(
                    booking,
                    payment_row_protected_ids=payment_row_protected_ids,
                ):
                    continue

                if not self._expiration_status_is_eligible(
                    booking.status, expiration.eligible_statuses
                ):
                    continue

                reference_ts = self._expiration_reference_timestamp(
                    booking, expiration.reference
                )
                if reference_ts is None:
                    continue

                limite = now - timedelta(hours=expiration.after_hours)
                if not (reference_ts < limite):
                    continue

                handler.execute(
                    ExpireBookingCommand(
                        booking_id=booking.id,
                        company_id=company_id,
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
        from app.shared.kernel.datetimes import as_naive_utc

        self.expirar_reservas_pendentes()

        tranca = self.db.query(Tranca).filter(Tranca.id == tranca_id).first()
        if not tranca:
            raise NotFoundError("Trança", str(tranca_id))
        if not tranca.ativo:
            raise BusinessRuleError("Trança não está ativa")

        duracao_consulta = self._duracao_minutos(
            tranca, service_image_id, ignorar_duracao_modelo
        )

        # Evita TypeError ao misturar offset-aware (ISO Z) com datetime.now() naive.
        data = as_naive_utc(data)
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
