"""
Service do painel administrativo.
Agrega dados de pagamentos, agenda, fila e CRM.

.. deprecated:: 2.11.0-r4-f8
    Toda a leitura deste service (dashboard, pagamentos, agenda, CRM) usava
    ``Agendamento`` legado como fonte. A tabela ``agendamentos`` foi
    removida (DROP físico — ADR-024 sunset / RFC-003 M11+) — reescrito
    para usar ``CoreBooking``/``CoreCatalog``/``CoreOffering`` (fonte da
    verdade desde R3-F2/R4-F4), fechando o débito residual apontado no
    gate R4-F7. Os schemas de resposta (``PagamentoAdminItem.agendamento_id``,
    ``AgendamentoAdminItem.status: StatusAgendamento``) foram mantidos
    inalterados para estabilidade do frontend — ``StatusAgendamento`` é
    apenas um alias de ``ReservationStatus`` (ver
    ``app.models.agendamento``), então valores de ``CoreBooking.status``
    são aceitos diretamente.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models.cliente import Cliente
from app.models.agendamento import StatusAgendamento, ReservationStatus, StatusPagamento
from app.models.fila import Fila, STATUS_FILA_ATIVOS
from app.models.financeiro import Financeiro, TipoMovimento
from app.models.payment import Payment, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver
from app.modules.booking.domain.value_objects.booking_types import BookingLifecycleStatus
from app.modules.catalog.domain.models import CoreCatalog
from app.schemas.admin import (
    AdminDashboardResponse,
    PagamentoAdminItem,
    AgendamentoAdminItem,
    ClienteCrmItem,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError


# ReservationStatus ORM / aliases FE → lifecycle canônico (política manual_status).
_ORM_STATUS_TO_LIFECYCLE = {
    ReservationStatus.PENDING_PAYMENT: BookingLifecycleStatus.PENDING.value,
    ReservationStatus.PENDING_APPROVAL: BookingLifecycleStatus.PENDING.value,
    ReservationStatus.WAITING_TIME_CONFIRMATION: BookingLifecycleStatus.PENDING.value,
    ReservationStatus.PENDENTE: BookingLifecycleStatus.PENDING.value,
    ReservationStatus.APPROVED: BookingLifecycleStatus.APPROVED.value,
    ReservationStatus.CONFIRMADO: BookingLifecycleStatus.APPROVED.value,
    ReservationStatus.IN_QUEUE: BookingLifecycleStatus.APPROVED.value,
    ReservationStatus.CHECKED_IN: BookingLifecycleStatus.APPROVED.value,
    ReservationStatus.IN_SERVICE: BookingLifecycleStatus.APPROVED.value,
    ReservationStatus.REJECTED: BookingLifecycleStatus.REJECTED.value,
    ReservationStatus.CANCELLED: BookingLifecycleStatus.CANCELLED.value,
    ReservationStatus.CANCELADO: BookingLifecycleStatus.CANCELLED.value,
    ReservationStatus.RESCHEDULED: BookingLifecycleStatus.RESCHEDULED.value,
    ReservationStatus.COMPLETED: BookingLifecycleStatus.COMPLETED.value,
    ReservationStatus.CONCLUIDO: BookingLifecycleStatus.COMPLETED.value,
    ReservationStatus.PAID: BookingLifecycleStatus.COMPLETED.value,
    ReservationStatus.NO_SHOW: BookingLifecycleStatus.NO_SHOW.value,
    ReservationStatus.EXPIRED: BookingLifecycleStatus.EXPIRED.value,
}


def _lifecycle_from_reservation_status(status: StatusAgendamento | str) -> str:
    """
    Mapeia status ORM/FE para lifecycle canônico da política de booking.

    Args:
        status: ``ReservationStatus`` ou string equivalente (ex.: ``confirmado``).

    Returns:
        Valor lifecycle (``pending``, ``approved``, ``cancelled``, …).

    Raises:
        ValidationError: Status desconhecido / não mapeável.
    """
    if isinstance(status, ReservationStatus):
        key = status
    else:
        try:
            key = ReservationStatus(str(status))
        except ValueError as exc:
            raise ValidationError(f"Status inválido: {status}") from exc
    lifecycle = _ORM_STATUS_TO_LIFECYCLE.get(key)
    if lifecycle is None:
        raise ValidationError(f"Status sem mapeamento de lifecycle: {key.value}")
    return lifecycle


class AdminService:
    """
    Service para operações administrativas do salão.

    Centraliza métricas do dashboard, listagens de pagamentos,
    gestão de agenda e dados de CRM.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db

    def obter_dashboard(self, company_id: int) -> AdminDashboardResponse:
        """
        Monta resumo agregado para o dashboard admin do tenant.

        FIX-02a: cada agregação filtra ``company_id`` na cláusula SQL
        (Cliente, CoreBooking, Fila, Financeiro) — sem post-filter e sem
        fallback ``salao-demo``.

        Args:
            company_id: Tenant efetivo (``companies.id``). Obrigatório;
                registros com ``company_id`` nulo não entram nas métricas.

        Returns:
            AdminDashboardResponse com totais de clientes, agenda,
            fila, pagamentos e receita do mês corrente do tenant.
        """
        hoje = date.today()
        inicio_mes = datetime(hoje.year, hoje.month, 1)
        fim_mes = datetime(hoje.year, hoje.month + 1, 1) if hoje.month < 12 else datetime(hoje.year + 1, 1, 1)

        total_clientes = self.db.query(func.count(Cliente.id)).filter(
            Cliente.company_id == company_id,
            Cliente.deleted_at.is_(None),
        ).scalar() or 0

        total_agendamentos = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        agendamentos_pendentes = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        aguardando_aprovacao = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.status.in_([
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        agendamentos_confirmados = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.status == ReservationStatus.APPROVED,
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        inicio_hoje = datetime.combine(hoje, datetime.min.time())
        fim_hoje = datetime.combine(hoje, datetime.max.time())

        agendamentos_hoje = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.scheduled_at >= inicio_hoje,
            CoreBooking.scheduled_at <= fim_hoje,
            CoreBooking.deleted_at.is_(None),
            CoreBooking.status != ReservationStatus.CANCELLED,
        ).scalar() or 0

        fila_hoje = self.db.query(func.count(Fila.id)).filter(
            Fila.company_id == company_id,
            Fila.data == hoje,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).scalar() or 0

        pagamentos_pendentes = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.deposit_paid.is_(False),
            CoreBooking.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        pagamentos_confirmados = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.company_id == company_id,
            CoreBooking.deposit_paid.is_(True),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        receita_mes = self.db.query(func.coalesce(func.sum(Financeiro.valor), 0)).filter(
            Financeiro.company_id == company_id,
            Financeiro.tipo == TipoMovimento.ENTRADA,
            Financeiro.data >= inicio_mes,
            Financeiro.data < fim_mes,
            Financeiro.deleted_at.is_(None),
        ).scalar() or Decimal("0")

        saidas_mes = self.db.query(func.coalesce(func.sum(Financeiro.valor), 0)).filter(
            Financeiro.company_id == company_id,
            Financeiro.tipo == TipoMovimento.SAIDA,
            Financeiro.data >= inicio_mes,
            Financeiro.data < fim_mes,
            Financeiro.deleted_at.is_(None),
        ).scalar() or Decimal("0")

        return AdminDashboardResponse(
            total_clientes=total_clientes,
            total_agendamentos=total_agendamentos,
            agendamentos_pendentes=agendamentos_pendentes,
            aguardando_aprovacao=aguardando_aprovacao,
            agendamentos_confirmados=agendamentos_confirmados,
            agendamentos_hoje=agendamentos_hoje,
            fila_hoje=fila_hoje,
            pagamentos_pendentes=pagamentos_pendentes,
            pagamentos_confirmados=pagamentos_confirmados,
            receita_mes=Decimal(str(receita_mes)),
            saldo_mes=Decimal(str(receita_mes)) - Decimal(str(saidas_mes)),
        )

    def listar_pagamentos(self, company_id: int) -> List[PagamentoAdminItem]:
        """
        Lista reservas (``CoreBooking``) com status de pagamento do sinal.

        Isolamento multi-tenant: filtra ``CoreBooking.company_id`` na query
        SQLAlchemy (não em memória).

        .. deprecated:: 2.11.0-r4-f8
            Antes lia ``Agendamento`` legado; reescrito para
            ``CoreBooking`` (tabela removida). ``comprovante_url`` passa a
            vir do ``Payment`` (DEPOSIT/SINAL) vinculado por
            ``booking_id`` — best-effort, ``None`` se não houver registro.

        Args:
            company_id: ID da empresa (tenant) ativa na requisição.

        Returns:
            Lista de PagamentoAdminItem ordenada por data decrescente.
        """
        rows = (
            self.db.query(CoreBooking, Cliente, CoreCatalog)
            .join(Cliente, CoreBooking.customer_id == Cliente.id)
            .join(CoreCatalog, CoreBooking.catalog_id == CoreCatalog.id)
            .options(joinedload(CoreBooking.offering))
            .filter(
                CoreBooking.deleted_at.is_(None),
                CoreBooking.company_id == company_id,
            )
            .order_by(CoreBooking.scheduled_at.desc())
            .all()
        )

        booking_ids = [booking.id for booking, _, _ in rows]
        comprovantes = {}
        if booking_ids:
            pagamentos = (
                self.db.query(Payment)
                .filter(
                    Payment.booking_id.in_(booking_ids),
                    Payment.tipo.in_([PaymentType.DEPOSIT, PaymentType.SINAL]),
                    Payment.comprovante_url.isnot(None),
                )
                .all()
            )
            comprovantes = {p.booking_id: p.comprovante_url for p in pagamentos}

        return [
            PagamentoAdminItem(
                agendamento_id=booking.id,
                cliente_nome=cliente.nome,
                tranca_nome=(
                    f"{catalog.name} — {booking.offering.name}"
                    if booking.offering and booking.offering.name
                    else catalog.name
                ),
                valor_sinal=booking.deposit_amount or Decimal("0"),
                sinal_pago=booking.deposit_paid,
                comprovante_url=comprovantes.get(booking.id),
                status_agendamento=booking.status,
                data_hora=booking.scheduled_at,
            )
            for booking, cliente, catalog in rows
        ]

    def listar_agendamentos(
        self,
        data_ref: Optional[date] = None,
    ) -> List[AgendamentoAdminItem]:
        """
        Lista reservas (``CoreBooking``) com dados de cliente, categoria e fila.

        .. deprecated:: 2.11.0-r4-f8
            Antes lia ``Agendamento`` legado (join com ``Tranca``);
            reescrito para ``CoreBooking`` + ``CoreCatalog``/``CoreOffering``
            (tabela ``agendamentos`` removida). ``tranca_id``/
            ``service_image_id`` no retorno são os IDs legado resolvidos
            via ACL (``legacy_tranca_id``/``legacy_service_image_id``) —
            estabilidade do schema para o frontend.

        Args:
            data_ref: Filtra por dia específico; None retorna todos futuros e recentes.

        Returns:
            Lista de AgendamentoAdminItem para gestão admin.
        """
        query = (
            self.db.query(CoreBooking, Cliente, CoreCatalog)
            .join(Cliente, CoreBooking.customer_id == Cliente.id)
            .join(CoreCatalog, CoreBooking.catalog_id == CoreCatalog.id)
            .options(joinedload(CoreBooking.offering))
            .filter(CoreBooking.deleted_at.is_(None))
        )

        if data_ref:
            inicio = datetime.combine(data_ref, datetime.min.time())
            fim = datetime.combine(data_ref, datetime.max.time())
            query = query.filter(
                CoreBooking.scheduled_at >= inicio,
                CoreBooking.scheduled_at <= fim,
            )
        else:
            limite = datetime.now() - timedelta(days=7)
            query = query.filter(CoreBooking.scheduled_at >= limite)

        rows = query.order_by(CoreBooking.scheduled_at.asc()).all()

        fila_map = {}
        if data_ref:
            fila_items = self.db.query(Fila).filter(
                Fila.data == data_ref,
                Fila.status.in_(STATUS_FILA_ATIVOS),
            ).all()
            fila_map = {f.cliente_id: f.posicao for f in fila_items}

        return [
            AgendamentoAdminItem(
                id=booking.id,
                cliente_id=cliente.id,
                cliente_nome=cliente.nome,
                cliente_telefone=cliente.telefone,
                tranca_id=catalog.legacy_tranca_id or catalog.id,
                tranca_nome=catalog.name,
                data_hora=booking.scheduled_at,
                status=booking.status,
                sinal_pago=booking.deposit_paid,
                na_fila=cliente.id in fila_map,
                posicao_fila=fila_map.get(cliente.id),
                service_image_id=booking.offering.legacy_service_image_id if booking.offering else None,
                imagem_url=booking.offering.image_url if booking.offering else None,
                imagem_label=booking.offering.name if booking.offering else None,
            )
            for booking, cliente, catalog in rows
        ]

    def atualizar_status_agendamento(
        self,
        agendamento_id: int,
        novo_status: StatusAgendamento,
        company_id: int,
    ) -> CoreBooking:
        """
        Atualiza status de uma reserva (``CoreBooking``) via gestão admin.

        FIX-02b-write: busca por ``id + company_id`` (inclui soft-deleted para
        bloquear reabertura); consome ``BookingPolicyResolver`` para matriz
        de transições e ``block_financial_reopen``; ao cancelar, alinha
        ``payment_status``/``deleted_at`` conforme política de cancelamento.

        Args:
            agendamento_id: ID do booking (``core_bookings.id``).
            novo_status: Novo status desejado (ORM/FE).
            company_id: Tenant efetivo da requisição (obrigatório).

        Returns:
            CoreBooking atualizado (ou inalterado se transição idempotente).

        Raises:
            NotFoundError: Booking inexistente para o tenant (inclui cross-tenant).
            ValidationError: Transição fora da matriz da política.
            ConflictError: Reabertura de cancelado/expirado ou status manual off.
            ValueError: ``company_id`` ausente/inválido.
        """
        if company_id is None or not isinstance(company_id, int) or company_id <= 0:
            raise ValueError("company_id é obrigatório para alterar status da agenda")

        # Inclui soft-deleted: reabertura de cancelado não deve virar 404 silencioso
        # que permita outro caminho; a política bloqueia com 409.
        booking = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == agendamento_id,
                CoreBooking.company_id == company_id,
            )
            .first()
        )
        if not booking:
            raise NotFoundError("Agendamento")

        policy = BookingPolicyResolver(self.db).resolve(company_id)
        manual = policy.manual_status
        if not manual.enabled:
            raise ConflictError("Alteração manual de status desabilitada para o tenant")

        current_lc = _lifecycle_from_reservation_status(booking.status)
        target_lc = _lifecycle_from_reservation_status(novo_status)

        if current_lc == target_lc:
            # Idempotente: mesmo lifecycle (ex.: cancelado ↔ cancelled).
            return booking

        if manual.block_financial_reopen:
            if current_lc in (
                BookingLifecycleStatus.CANCELLED.value,
                BookingLifecycleStatus.EXPIRED.value,
            ):
                raise ConflictError(
                    "Não é permitido reabrir booking cancelado ou expirado"
                )
            payment_status = booking.payment_status
            payment_value = (
                payment_status.value
                if hasattr(payment_status, "value")
                else str(payment_status)
            )
            if payment_value == StatusPagamento.CANCELLED.value and target_lc not in (
                BookingLifecycleStatus.CANCELLED.value,
                BookingLifecycleStatus.EXPIRED.value,
            ):
                raise ConflictError(
                    "Não é permitido reabrir janela financeira de booking cancelado"
                )

        allowed = manual.allowed_transitions.get(current_lc, ())
        if target_lc not in allowed:
            raise ValidationError(
                f"Transição de status não permitida: {current_lc} → {target_lc}"
            )

        # Snapshot de proteção financeira — nunca limpar ao mutar.
        previous_payment_status = booking.payment_status
        previous_deleted_at = booking.deleted_at

        booking.status = novo_status

        if target_lc == BookingLifecycleStatus.CANCELLED.value:
            if policy.cancellation.set_payment_cancelled:
                booking.payment_status = StatusPagamento.CANCELLED
            if policy.cancellation.soft_delete:
                booking.deleted_at = previous_deleted_at or datetime.utcnow()
        elif target_lc == BookingLifecycleStatus.EXPIRED.value:
            # Expiração via PATCH só se a matriz permitir; soft-delete alinhado
            # ao path de repositório (não altera payment_status por default).
            booking.deleted_at = previous_deleted_at or datetime.utcnow()

        # Preserva CANCELLED / deleted_at se já estavam definidos (fail-closed).
        if (
            hasattr(previous_payment_status, "value")
            and previous_payment_status.value == StatusPagamento.CANCELLED.value
        ) or previous_payment_status == StatusPagamento.CANCELLED:
            booking.payment_status = StatusPagamento.CANCELLED
        if previous_deleted_at is not None:
            booking.deleted_at = previous_deleted_at

        self.db.commit()
        self.db.refresh(booking)
        return booking

    def listar_crm_clientes(self) -> List[ClienteCrmItem]:
        """
        Lista clientes com métricas de CRM (visitas, gasto, reativação).

        .. deprecated:: 2.11.0-r4-f8
            Antes agregava sobre ``Agendamento`` legado; reescrito para
            ``CoreBooking`` (tabela ``agendamentos`` removida). Considera
            ``PENDENTE``/``CONFIRMADO`` (aliases legado de
            ``ReservationStatus``) via os valores equivalentes
            ``PENDING_PAYMENT``/``APPROVED`` para refletir bookings
            core-only.

        Returns:
            Lista de ClienteCrmItem ordenada por última visita.
        """
        clientes = self.db.query(Cliente).filter(
            Cliente.deleted_at.is_(None)
        ).all()

        limite_inativo = datetime.now() - timedelta(days=60)
        resultado: List[ClienteCrmItem] = []

        for cliente in clientes:
            bookings = self.db.query(CoreBooking).filter(
                CoreBooking.customer_id == cliente.id,
                CoreBooking.deleted_at.is_(None),
            ).all()

            confirmados = [
                b for b in bookings
                if b.status == ReservationStatus.APPROVED or b.deposit_paid
            ]
            ultima_visita = max(
                (b.scheduled_at for b in bookings if b.status != ReservationStatus.CANCELLED),
                default=None,
            )

            total_gasto = Decimal("0")
            for booking in confirmados:
                if booking.deposit_paid and booking.deposit_amount is not None:
                    total_gasto += Decimal(str(booking.deposit_amount))

            if not bookings:
                status_crm = "novo"
            elif ultima_visita and ultima_visita < limite_inativo:
                status_crm = "inativo"
            elif any(
                b.status == ReservationStatus.PENDING_PAYMENT and not b.deposit_paid
                for b in bookings
            ):
                status_crm = "pendente_pagamento"
            else:
                status_crm = "ativo"

            resultado.append(
                ClienteCrmItem(
                    id=cliente.id,
                    nome=cliente.nome,
                    telefone=cliente.telefone,
                    email=cliente.email,
                    total_agendamentos=len(bookings),
                    agendamentos_confirmados=len(confirmados),
                    total_gasto=total_gasto,
                    ultima_visita=ultima_visita,
                    status_crm=status_crm,
                )
            )

        resultado.sort(
            key=lambda c: c.ultima_visita or datetime.min,
            reverse=True,
        )
        return resultado
