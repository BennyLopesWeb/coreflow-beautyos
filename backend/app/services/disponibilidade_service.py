"""
Service de Disponibilidade
Lógica de negócio para cálculo de horários disponíveis.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Set, FrozenSet, Any

from app.models.agendamento import ReservationStatus, StatusPagamento, STATUS_OCUPAM_VAGA
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.agendamento import HorarioDisponivel
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.core.logging_config import get_logger
from app.utils.service_image_precos import resolver_precos_imagem
from app.services.agenda_dia_service import AgendaDiaService
from app.modules.booking.domain.policy.cancel_window import ensure_utc
from app.modules.booking.domain.policy.activation import (
    calculate_minimum_activation_cents,
    money_to_cents,
)
from app.modules.booking.domain.policy.paid_amount import (
    load_effective_paid_snapshots,
    snapshots_as_dicts,
)

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

# payment_status que sugerem dinheiro recebido — usados só para detectar
# divergência (flags sem valor pago mensurável) → fail-closed.
_FLAG_PAID_PAYMENT_STATUS_VALUES: FrozenSet[str] = frozenset(
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

    @staticmethod
    def _money_to_cents(value) -> Optional[int]:
        """
        Converte valor monetário para centavos (delegado à política compartilhada).

        Args:
            value: Valor em reais.

        Returns:
            Centavos >= 0, ou ``None`` se inválido.
        """
        return money_to_cents(value)

    @staticmethod
    def _get_minimum_activation_cents(total_service_cents: int) -> int:
        """
        Calcula o mínimo de ativação (delegado à política compartilhada).

        Args:
            total_service_cents: Total do serviço em centavos (> 0).

        Returns:
            Mínimo de ativação em centavos.
        """
        return calculate_minimum_activation_cents(total_service_cents)

    def _load_payment_activation_snapshots(
        self, booking_ids: List[int], *, company_id: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Pré-carrega somas pagas e flags de processamento por booking.

        Delega à política compartilhada ``load_effective_paid_snapshots``
        (RECONCILE-DEPOSIT-SOURCES-01) — mesma fonte da ativação.

        Args:
            booking_ids: IDs de ``core_bookings``.
            company_id: Tenant opcional para filtrar ``CorePayment``.

        Returns:
            Mapa ``booking_id → {paid_cents, has_processing, has_paid_rows}``.

        Raises:
            Exception: Falha de consulta (caller aplica fail-closed).
        """
        return snapshots_as_dicts(
            load_effective_paid_snapshots(
                self.db, booking_ids, company_id=company_id
            )
        )

    def _has_minimum_activation_payment(
        self,
        booking,
        *,
        payment_snapshots: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> bool:
        """
        Indica se a reserva está ativa pelo mínimo financeiro e não deve
        expirar automaticamente (FIX-EXPIRATION-02C).

        Reserva ativa quando ``paid_cents >= min(ceil(total*20%), 10000)``.
        Pagamento abaixo do mínimo **não** ativa (pode expirar).
        ``processando``, total inválido, divergência flag/valor ou erro →
        fail-closed (não expira). Não altera dados financeiros.

        Args:
            booking: Candidato à expiração.
            payment_snapshots: Snapshot financeiro pré-carregado do lote.

        Returns:
            ``True`` se a expiração deve ser bloqueada (ativa ou fail-closed).
        """
        company_id = getattr(booking, "company_id", None)
        booking_id = getattr(booking, "id", None)

        try:
            if booking_id is None:
                logger.warning(
                    "Expiração: booking sem id — fail-closed company_id=%s",
                    company_id,
                )
                return True

            total_cents = self._money_to_cents(getattr(booking, "price_total", None))
            if total_cents is None or total_cents <= 0:
                logger.warning(
                    "Expiração: booking_id=%s company_id=%s sem price_total "
                    "válido — fail-closed",
                    booking_id,
                    company_id,
                )
                return True

            if payment_snapshots is None:
                payment_snapshots = self._load_payment_activation_snapshots(
                    [int(booking_id)],
                    company_id=int(company_id) if company_id is not None else None,
                )
            snap = payment_snapshots.get(
                int(booking_id),
                {"paid_cents": 0, "has_processing": False, "has_paid_rows": False},
            )
            # Fonte canônica: ledger. deposit_amount é cotação comercial e
            # não entra na soma.
            paid_cents = int(snap.get("paid_cents") or 0)

            if snap.get("has_processing"):
                logger.info(
                    "Expiração: booking_id=%s company_id=%s com pagamento "
                    "processando — fail-closed (não conta como pago)",
                    booking_id,
                    company_id,
                )
                return True

            if snap.get("has_source_divergence") or not snap.get(
                "is_reconciled", True
            ):
                logger.warning(
                    "Expiração: booking_id=%s company_id=%s divergência "
                    "Payment(%s) vs CorePayment(%s) — fail-closed",
                    booking_id,
                    company_id,
                    snap.get("payment_cents"),
                    snap.get("core_payment_cents"),
                )
                return True

            pay_status = self._booking_payment_status_value(booking)
            flags_suggest_paid = bool(getattr(booking, "deposit_paid", False)) or (
                pay_status in _FLAG_PAID_PAYMENT_STATUS_VALUES
            )
            if flags_suggest_paid and paid_cents <= 0:
                logger.warning(
                    "Expiração: booking_id=%s company_id=%s divergência "
                    "financeira (flags pagos sem valor) — fail-closed",
                    booking_id,
                    company_id,
                )
                return True

            from app.modules.booking.domain.policy.activation import (
                resolve_booking_minimum_activation_cents,
            )

            try:
                minimum = resolve_booking_minimum_activation_cents(booking)
            except ValueError:
                minimum = self._get_minimum_activation_cents(total_cents)
            if paid_cents >= minimum:
                logger.info(
                    "Expiração: booking_id=%s company_id=%s ativo "
                    "(paid_cents=%s >= minimum=%s) — não expira",
                    booking_id,
                    company_id,
                    paid_cents,
                    minimum,
                )
                return True

            if paid_cents > 0:
                logger.info(
                    "Expiração: booking_id=%s company_id=%s pagamento abaixo "
                    "do mínimo (paid_cents=%s < minimum=%s) — pode expirar",
                    booking_id,
                    company_id,
                    paid_cents,
                    minimum,
                )
            return False
        except Exception:
            logger.warning(
                "Falha ao avaliar ativação financeira booking_id=%s "
                "company_id=%s — expiração ignorada (fail-closed)",
                booking_id,
                company_id,
                exc_info=True,
            )
            return True

    def _expirar_core_bookings_pendentes(self) -> int:
        """
        Expira ``CoreBooking`` elegível sem ativação financeira mínima
        (FIX-EXPIRATION-02A/02B/02C).

        Candidatos SQL: status PENDING-like seguros, não soft-deleted.
        Por tenant: ``enabled``, ``after_hours``, ``reference``,
        ``eligible_statuses``. Antes do handler, bloqueia reservas ativas
        via ``_has_minimum_activation_payment``
        (``min(ceil(total*20%), R$100)``).

        Comparação exclusiva: ``reference_ts < now - after_hours``.

        FIX-EXPIRATION-02C: ``require_unpaid_deposit=false`` não amplia
        elegibilidade de reservas ativas. Pagamento abaixo do mínimo não
        ativa e pode expirar. ``touch_payment_status`` sem efeito;
        ``payment_status`` nunca é alterado aqui.

        Falhas isoladas (resolve, tenant, handler, financeiro) não
        interrompem o lote — best-effort com log.

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
        # Ativação financeira (mínimo 20%/R$100) é aplicada antes do handler.
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
            payment_snapshots = self._load_payment_activation_snapshots(booking_ids)
        except Exception:
            logger.warning(
                "Falha ao pré-carregar snapshots financeiros do lote de "
                "expiração — todos os candidatos tratados como protegidos "
                "(fail-closed)",
                exc_info=True,
            )
            payment_snapshots = {
                bid: {
                    "paid_cents": 0,
                    "has_processing": True,
                    "has_paid_rows": False,
                }
                for bid in booking_ids
            }

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
                # elegibilidade; reserva ativa (mínimo atingido) nunca expira.
                if expiration.require_unpaid_deposit is False:
                    pass

                if self._has_minimum_activation_payment(
                    booking,
                    payment_snapshots=payment_snapshots,
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
