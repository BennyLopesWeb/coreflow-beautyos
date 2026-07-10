"""
Service do painel administrativo.
Agrega dados de pagamentos, agenda, fila e CRM.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models.cliente import Cliente
from app.models.agendamento import Agendamento, StatusAgendamento, ReservationStatus
from app.models.tranca import Tranca
from app.models.fila import Fila, STATUS_FILA_ATIVOS
from app.models.financeiro import Financeiro, TipoMovimento
from app.models.payment import Payment, PaymentStatus
from app.schemas.admin import (
    AdminDashboardResponse,
    PagamentoAdminItem,
    AgendamentoAdminItem,
    ClienteCrmItem,
)
from app.services.agendamento_service import AgendamentoService
from app.core.exceptions import NotFoundError
from app.utils.service_image_precos import resolver_precos_imagem


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
        self.agendamento_service = AgendamentoService(db)

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

        total_agendamentos = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.deleted_at.is_(None)
        ).scalar() or 0

        agendamentos_pendentes = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
                StatusAgendamento.PENDENTE,
            ]),
            Agendamento.deleted_at.is_(None),
        ).scalar() or 0

        aguardando_aprovacao = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.status.in_([
                ReservationStatus.PENDING_APPROVAL,
                ReservationStatus.WAITING_TIME_CONFIRMATION,
            ]),
            Agendamento.deleted_at.is_(None),
        ).scalar() or 0

        agendamentos_confirmados = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.status.in_([
                ReservationStatus.APPROVED,
                StatusAgendamento.CONFIRMADO,
            ]),
            Agendamento.deleted_at.is_(None),
        ).scalar() or 0

        inicio_hoje = datetime.combine(hoje, datetime.min.time())
        fim_hoje = datetime.combine(hoje, datetime.max.time())

        agendamentos_hoje = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.data_hora >= inicio_hoje,
            Agendamento.data_hora <= fim_hoje,
            Agendamento.deleted_at.is_(None),
            Agendamento.status != StatusAgendamento.CANCELADO,
        ).scalar() or 0

        fila_hoje = self.db.query(func.count(Fila.id)).filter(
            Fila.data == hoje,
            Fila.status.in_(STATUS_FILA_ATIVOS),
        ).scalar() or 0

        pagamentos_pendentes = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.sinal_pago.is_(False),
            Agendamento.status.in_([
                ReservationStatus.PENDING_PAYMENT,
                ReservationStatus.PENDING_APPROVAL,
                StatusAgendamento.PENDENTE,
            ]),
            Agendamento.deleted_at.is_(None),
        ).scalar() or 0

        pagamentos_confirmados = self.db.query(func.count(Agendamento.id)).filter(
            Agendamento.sinal_pago.is_(True),
            Agendamento.deleted_at.is_(None),
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
        Lista agendamentos com status de pagamento do sinal.

        Returns:
            Lista de PagamentoAdminItem ordenada por data decrescente.
        """
        rows = (
            self.db.query(Agendamento, Cliente, Tranca)
            .join(Cliente, Agendamento.cliente_id == Cliente.id)
            .join(Tranca, Agendamento.tranca_id == Tranca.id)
            .options(joinedload(Agendamento.service_image))
            .filter(Agendamento.deleted_at.is_(None))
            .order_by(Agendamento.data_hora.desc())
            .all()
        )

        from app.utils.service_image_precos import resolver_precos_imagem
        from app.schemas.service_image import _label_modelo

        def _valor_sinal_ag(ag, tranca):
            if ag.valor_sinal is not None:
                return ag.valor_sinal
            if ag.service_image:
                try:
                    return resolver_precos_imagem(ag.service_image)["valor_sinal"]
                except ValueError:
                    pass
            return Decimal("0")

        return [
            PagamentoAdminItem(
                agendamento_id=ag.id,
                cliente_nome=cliente.nome,
                tranca_nome=(
                    f"{tranca.nome} — {_label_modelo(ag.service_image)}"
                    if ag.service_image
                    else tranca.nome
                ),
                valor_sinal=_valor_sinal_ag(ag, tranca),
                sinal_pago=ag.sinal_pago,
                comprovante_url=ag.comprovante_url,
                status_agendamento=ag.status,
                data_hora=ag.data_hora,
            )
            for ag, cliente, tranca in rows
        ]

    def listar_agendamentos(
        self,
        data_ref: Optional[date] = None,
    ) -> List[AgendamentoAdminItem]:
        """
        Lista agendamentos com dados de cliente, trança e fila.

        Args:
            data_ref: Filtra por dia específico; None retorna todos futuros e recentes.

        Returns:
            Lista de AgendamentoAdminItem para gestão admin.
        """
        query = (
            self.db.query(Agendamento, Cliente, Tranca)
            .join(Cliente, Agendamento.cliente_id == Cliente.id)
            .join(Tranca, Agendamento.tranca_id == Tranca.id)
            .options(joinedload(Agendamento.service_image))
            .filter(Agendamento.deleted_at.is_(None))
        )

        if data_ref:
            inicio = datetime.combine(data_ref, datetime.min.time())
            fim = datetime.combine(data_ref, datetime.max.time())
            query = query.filter(
                Agendamento.data_hora >= inicio,
                Agendamento.data_hora <= fim,
            )
        else:
            limite = datetime.now() - timedelta(days=7)
            query = query.filter(Agendamento.data_hora >= limite)

        rows = query.order_by(Agendamento.data_hora.asc()).all()

        fila_map = {}
        if data_ref:
            fila_items = self.db.query(Fila).filter(
                Fila.data == data_ref,
                Fila.status.in_(STATUS_FILA_ATIVOS),
            ).all()
            fila_map = {f.cliente_id: f.posicao for f in fila_items}

        return [
            AgendamentoAdminItem(
                id=ag.id,
                cliente_id=cliente.id,
                cliente_nome=cliente.nome,
                cliente_telefone=cliente.telefone,
                tranca_id=tranca.id,
                tranca_nome=tranca.nome,
                data_hora=ag.data_hora,
                status=ag.status,
                sinal_pago=ag.sinal_pago,
                na_fila=cliente.id in fila_map,
                posicao_fila=fila_map.get(cliente.id),
                service_image_id=ag.service_image_id,
                imagem_url=ag.service_image.url if ag.service_image else None,
                imagem_label=(
                    f"Foto {ag.service_image.ordem}" if ag.service_image else None
                ),
            )
            for ag, cliente, tranca in rows
        ]

    def atualizar_status_agendamento(
        self,
        agendamento_id: int,
        novo_status: StatusAgendamento,
    ) -> Agendamento:
        """
        Atualiza status de um agendamento (gestão admin).

        Args:
            agendamento_id: ID do agendamento.
            novo_status: Novo status desejado.

        Returns:
            Agendamento atualizado.

        Raises:
            NotFoundError: Se agendamento não existir.
        """
        agendamento = self.db.query(Agendamento).filter(
            Agendamento.id == agendamento_id,
            Agendamento.deleted_at.is_(None),
        ).first()

        if not agendamento:
            raise NotFoundError("Agendamento não encontrado")

        agendamento.status = novo_status
        self.db.commit()
        self.db.refresh(agendamento)
        return agendamento

    def listar_crm_clientes(self) -> List[ClienteCrmItem]:
        """
        Lista clientes com métricas de CRM (visitas, gasto, reativação).

        Returns:
            Lista de ClienteCrmItem ordenada por última visita.
        """
        clientes = self.db.query(Cliente).filter(
            Cliente.deleted_at.is_(None)
        ).all()

        limite_inativo = datetime.now() - timedelta(days=60)
        resultado: List[ClienteCrmItem] = []

        for cliente in clientes:
            agendamentos = self.db.query(Agendamento).filter(
                Agendamento.cliente_id == cliente.id,
                Agendamento.deleted_at.is_(None),
            ).all()

            confirmados = [a for a in agendamentos if a.status == StatusAgendamento.CONFIRMADO or a.sinal_pago]
            ultima_visita = max(
                (a.data_hora for a in agendamentos if a.status != StatusAgendamento.CANCELADO),
                default=None,
            )

            total_gasto = Decimal("0")
            for ag in confirmados:
                tranca = self.db.query(Tranca).filter(Tranca.id == ag.tranca_id).first()
                if tranca and ag.sinal_pago:
                    if ag.valor_sinal is not None:
                        total_gasto += Decimal(str(ag.valor_sinal))
                    elif ag.service_image:
                        try:
                            total_gasto += Decimal(
                                str(resolver_precos_imagem(ag.service_image)["valor_sinal"])
                            )
                        except ValueError:
                            pass

            if not agendamentos:
                status_crm = "novo"
            elif ultima_visita and ultima_visita < limite_inativo:
                status_crm = "inativo"
            elif any(a.status == StatusAgendamento.PENDENTE and not a.sinal_pago for a in agendamentos):
                status_crm = "pendente_pagamento"
            else:
                status_crm = "ativo"

            resultado.append(
                ClienteCrmItem(
                    id=cliente.id,
                    nome=cliente.nome,
                    telefone=cliente.telefone,
                    email=cliente.email,
                    total_agendamentos=len(agendamentos),
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
