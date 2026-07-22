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
from app.models.agendamento import StatusAgendamento, ReservationStatus
from app.models.fila import Fila, STATUS_FILA_ATIVOS
from app.models.financeiro import Financeiro, TipoMovimento
from app.models.payment import Payment, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.catalog.domain.models import CoreCatalog
from app.schemas.admin import (
    AdminDashboardResponse,
    PagamentoAdminItem,
    AgendamentoAdminItem,
    ClienteCrmItem,
)
from app.core.exceptions import NotFoundError


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

    def obter_dashboard(self) -> AdminDashboardResponse:
        """
        Monta resumo agregado para o dashboard admin.

        Returns:
            AdminDashboardResponse com totais de clientes, agenda,
            fila, pagamentos e receita do mês corrente.
        """
        hoje = date.today()
        inicio_mes = datetime(hoje.year, hoje.month, 1)
        fim_mes = datetime(hoje.year, hoje.month + 1, 1) if hoje.month < 12 else datetime(hoje.year + 1, 1, 1)

        total_clientes = self.db.query(func.count(Cliente.id)).filter(
            Cliente.deleted_at.is_(None)
        ).scalar() or 0

        total_agendamentos = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.deleted_at.is_(None)
        ).scalar() or 0

        agendamentos_pendentes = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        aguardando_aprovacao = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.status.in_([
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        agendamentos_confirmados = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.status == ReservationStatus.APPROVED,
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        inicio_hoje = datetime.combine(hoje, datetime.min.time())
        fim_hoje = datetime.combine(hoje, datetime.max.time())

        agendamentos_hoje = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.scheduled_at >= inicio_hoje,
            CoreBooking.scheduled_at <= fim_hoje,
            CoreBooking.deleted_at.is_(None),
            CoreBooking.status != ReservationStatus.CANCELLED,
        ).scalar() or 0

        fila_hoje = self.db.query(func.count(Fila.id)).filter(
            Fila.data == hoje,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).scalar() or 0

        pagamentos_pendentes = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.deposit_paid.is_(False),
            CoreBooking.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
            ]),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        pagamentos_confirmados = self.db.query(func.count(CoreBooking.id)).filter(
            CoreBooking.deposit_paid.is_(True),
            CoreBooking.deleted_at.is_(None),
        ).scalar() or 0

        receita_mes = self.db.query(func.coalesce(func.sum(Financeiro.valor), 0)).filter(
            Financeiro.tipo == TipoMovimento.ENTRADA,
            Financeiro.data >= inicio_mes,
            Financeiro.data < fim_mes,
            Financeiro.deleted_at.is_(None),
        ).scalar() or Decimal("0")

        saidas_mes = self.db.query(func.coalesce(func.sum(Financeiro.valor), 0)).filter(
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

    def listar_pagamentos(self) -> List[PagamentoAdminItem]:
        """
        Lista reservas (``CoreBooking``) com status de pagamento do sinal.

        .. deprecated:: 2.11.0-r4-f8
            Antes lia ``Agendamento`` legado; reescrito para
            ``CoreBooking`` (tabela removida). ``comprovante_url`` passa a
            vir do ``Payment`` (DEPOSIT/SINAL) vinculado por
            ``booking_id`` — best-effort, ``None`` se não houver registro.

        Returns:
            Lista de PagamentoAdminItem ordenada por data decrescente.
        """
        rows = (
            self.db.query(CoreBooking, Cliente, CoreCatalog)
            .join(Cliente, CoreBooking.customer_id == Cliente.id)
            .join(CoreCatalog, CoreBooking.catalog_id == CoreCatalog.id)
            .options(joinedload(CoreBooking.offering))
            .filter(CoreBooking.deleted_at.is_(None))
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
    ) -> CoreBooking:
        """
        Atualiza status de uma reserva (``CoreBooking``) via gestão admin.

        .. deprecated:: 2.11.0-r4-f8
            Antes atualizava ``Agendamento`` legado; reescrito para
            ``CoreBooking`` (tabela ``agendamentos`` removida —
            ``StatusAgendamento`` é apenas um alias de
            ``ReservationStatus``, aceito diretamente por
            ``CoreBooking.status``).

        Args:
            agendamento_id: ID do booking (``core_bookings.id``).
            novo_status: Novo status desejado.

        Returns:
            CoreBooking atualizado.

        Raises:
            NotFoundError: Se o booking não existir.
        """
        booking = self.db.query(CoreBooking).filter(
            CoreBooking.id == agendamento_id,
            CoreBooking.deleted_at.is_(None),
        ).first()

        if not booking:
            raise NotFoundError("Agendamento não encontrado")

        booking.status = novo_status
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
