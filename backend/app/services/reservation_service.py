"""
Service de Reservas (Reservation).
Ciclo completo: criar, pagar sinal, aprovar, rejeitar, reagendar, concluir.

R3-F2 (ADR-027/ADR-033/RFC-003 M4): os métodos de **escrita do booking**
(``criar``, ``criar_de_schema``, ``aprovar``, ``rejeitar``, ``cancelar``)
foram removidos — sempre levantam ``BusinessRuleError`` apontando para
``/v1/bookings``. As assinaturas e DocStrings são mantidas por
compatibilidade de referência/import. Os demais métodos (listagem/leitura,
``confirmar_deposito``, ``concluir``, reagendamento e pagamentos) continuam
ativos para dados legado históricos.

R4-F6 (ADR-024 sunset / RFC-003 M10): ``aceitar_reagendamento`` deixou de
criar ``Schedule`` — bookings novos são sempre core-only, sem entidade
``Schedule`` associada; o método permanece só para transição de status de
``Agendamento`` histórico (sem router HTTP ativo).
"""
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
from app.schemas.reservation import ReservationCreate
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.service_image_service import ServiceImageService
from app.services.schedule_service import ScheduleService
from app.services.payment_reservation_service import PaymentReservationService
from app.utils.service_image_precos import resolver_precos_imagem
from app.core.logging_config import get_logger

logger = get_logger("reservation_service")


class ReservationService:
    """
    Orquestra reservas, agenda, pagamentos e notificações.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db
        self.disponibilidade = DisponibilidadeService(db)
        self.schedule = ScheduleService(db)
        self.payments = PaymentReservationService(db)
        self.images = ServiceImageService(db)

    def _query_base(self):
        """Query base com joins."""
        return (
            self.db.query(Agendamento)
            .options(
                joinedload(Agendamento.service_image),
                joinedload(Agendamento.tranca),
                joinedload(Agendamento.cliente),
            )
            .filter(Agendamento.deleted_at.is_(None))
        )

    def _enriquecer(self, ag: Agendamento) -> dict:
        """
        Serializa reserva com nomes e preenche campos legados ausentes.

        Args:
            ag: Agendamento.

        Returns:
            Dict para ReservationResponse.
        """
        from app.schemas.service_image import _label_modelo
        from app.schemas.reservation import ReservationResponse

        valor_total = ag.valor_total
        valor_sinal = ag.valor_sinal
        valor_restante = ag.valor_restante
        percentual_sinal = ag.percentual_sinal
        service_image_id = ag.service_image_id

        if ag.service_image:
            if service_image_id is None:
                service_image_id = ag.service_image.id
            try:
                precos = resolver_precos_imagem(ag.service_image, ag.tranca)
                if valor_total is None:
                    valor_total = precos["valor_total"]
                if valor_sinal is None:
                    valor_sinal = precos["valor_sinal"]
                if valor_restante is None:
                    valor_restante = precos["valor_restante"]
                if percentual_sinal is None:
                    percentual_sinal = Decimal(str(ag.service_image.percentual_sinal or "0.30"))
            except ValueError:
                pass

        if percentual_sinal is None:
            percentual_sinal = Decimal("0.30")
        if valor_total is None:
            valor_total = Decimal("0")
        if valor_sinal is None:
            valor_sinal = Decimal("0")
        if valor_restante is None:
            valor_restante = Decimal("0")
        if service_image_id is None:
            service_image_id = 0

        payload = {
            "id": ag.id,
            "cliente_id": ag.cliente_id,
            "tranca_id": ag.tranca_id,
            "service_image_id": service_image_id,
            "data_hora": ag.data_hora,
            "horario_aprovado": ag.horario_aprovado,
            "valor_total": valor_total,
            "percentual_sinal": percentual_sinal,
            "valor_sinal": valor_sinal,
            "valor_restante": valor_restante,
            "sinal_pago": ag.sinal_pago,
            "status_pagamento": ag.status_pagamento,
            "status": ag.status,
            "observacoes": ag.observacoes,
            "motivo_rejeicao": ag.motivo_rejeicao,
            "horario_sugerido": ag.horario_sugerido,
            "mensagem_reagendamento": ag.mensagem_reagendamento,
            "comprovante_url": ag.comprovante_url,
            "created_at": ag.created_at,
            "updated_at": ag.updated_at,
        }
        data = ReservationResponse.model_validate(payload).model_dump()
        data["cliente_nome"] = ag.cliente.nome if ag.cliente else None
        data["tranca_nome"] = ag.tranca.nome if ag.tranca else None
        data["modelo_nome"] = _label_modelo(ag.service_image) if ag.service_image else None
        return data

    def listar(
        self,
        status: Optional[ReservationStatus] = None,
        cliente_id: Optional[int] = None,
        data_ref: Optional[datetime] = None,
        pendentes: bool = False,
        company_id: Optional[int] = None,
    ) -> List[Agendamento]:
        """
        Lista reservas com filtros opcionais.

        Args:
            status: Filtrar por status.
            cliente_id: Filtrar por cliente.
            data_ref: Filtrar por dia.
            pendentes: Apenas reservas que exigem ação da profissional.
            company_id: Filtrar por tenant BeautyOS.

        Returns:
            Lista de reservas.
        """
        q = self._query_base()
        if company_id is not None:
            q = q.filter(Agendamento.company_id == company_id)
        if pendentes:
            q = q.filter(
                Agendamento.status.in_([
                    ReservationStatus.PENDING_PAYMENT,
                    ReservationStatus.PENDING_APPROVAL,
                    ReservationStatus.WAITING_TIME_CONFIRMATION,
                    ReservationStatus.PENDENTE,
                ])
            )
        if status:
            q = q.filter(Agendamento.status == status)
        if cliente_id:
            q = q.filter(Agendamento.cliente_id == cliente_id)
        if data_ref:
            inicio = data_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            fim = inicio + timedelta(days=1)
            q = q.filter(Agendamento.data_hora >= inicio, Agendamento.data_hora < fim)
        return q.order_by(Agendamento.created_at.desc()).all()

    def obter(self, reservation_id: int) -> Agendamento:
        """
        Obtém reserva por ID.

        Args:
            reservation_id: ID da reserva.

        Returns:
            Agendamento.

        Raises:
            NotFoundError: Se não existir.
        """
        ag = self._query_base().filter(Agendamento.id == reservation_id).first()
        if not ag:
            raise NotFoundError("Reserva", str(reservation_id))
        return ag

    def criar(
        self,
        cliente_id: int,
        tranca_id: int,
        service_image_id: int,
        data_hora: datetime,
        observacoes: Optional[str] = None,
    ) -> Agendamento:
        """
        **Removido em R3-F2** — criação de reserva via legado.

        Delegava a ``criar_de_schema``. Ambos foram removidos (ADR-027/
        ADR-033/RFC-003 M4): use ``POST /v1/bookings`` (booking core-only).

        Args:
            cliente_id: ID do cliente.
            tranca_id: ID da categoria.
            service_image_id: ID do modelo.
            data_hora: Horário solicitado.
            observacoes: Notas opcionais.

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        return self.criar_de_schema(ReservationCreate(
            cliente_id=cliente_id,
            tranca_id=tranca_id,
            service_image_id=service_image_id,
            data_hora=data_hora,
            observacoes=observacoes,
        ))

    def criar_de_schema(self, data: ReservationCreate, company_id: Optional[int] = None) -> Agendamento:
        """
        **Removido em R3-F2** — criação de reserva via legado.

        Antes criava ``Agendamento`` com snapshot de preço/duração/sinal do
        modelo e publicava ``reservation.created``. O booking write path
        legado foi removido (ADR-027/ADR-033/RFC-003 M4) — use
        ``POST /v1/bookings`` (flag ``booking.core.enabled``). O dual-write
        outbound que existia a partir do path core (``project_create_booking``)
        foi removido definitivamente em R4-F3 — bookings são sempre
        core-only.

        Args:
            data: Dados validados.
            company_id: Tenant BeautyOS (herdado da categoria se omitido).

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def confirmar_deposito(
        self,
        reservation_id: int,
        transaction_id: Optional[str] = None,
        comprovante_url: Optional[str] = None,
    ) -> Agendamento:
        """
        Confirma pagamento do sinal → PENDING_APPROVAL.

        Args:
            reservation_id: ID da reserva.
            transaction_id: ID da transação.
            comprovante_url: URL do comprovante.

        Returns:
            Reserva atualizada.
        """
        self.payments.confirmar_deposito(reservation_id, transaction_id, comprovante_url)
        ag = self.obter(reservation_id)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_reserva_aguardando_aprovacao(reservation_id)
        return ag

    def aprovar(self, reservation_id: int) -> Agendamento:
        """
        **Removido em R3-F2** — aprovação de reserva via legado.

        Antes fazia ``PENDING_APPROVAL → APPROVED`` + criava ``Schedule``.
        Use ``POST /v1/bookings/{id}/approve`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def rejeitar(self, reservation_id: int, motivo: str) -> Agendamento:
        """
        **Removido em R3-F2** — rejeição de reserva via legado.

        Use ``POST /v1/bookings/{id}/reject`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo da rejeição.

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def solicitar_reagendamento(
        self,
        reservation_id: int,
        novo_horario: datetime,
        mensagem: Optional[str] = None,
    ) -> Agendamento:
        """
        Admin sugere novo horário → WAITING_TIME_CONFIRMATION.

        Args:
            reservation_id: ID da reserva.
            novo_horario: Horário proposto.
            mensagem: Mensagem ao cliente.

        Returns:
            Reserva atualizada.
        """
        ag = self.obter(reservation_id)
        ag.status = ReservationStatus.WAITING_TIME_CONFIRMATION
        ag.horario_sugerido = novo_horario
        ag.mensagem_reagendamento = mensagem
        self.db.commit()

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_horario_sugerido(reservation_id)
        return self.obter(reservation_id)

    def aceitar_reagendamento(self, reservation_id: int) -> Agendamento:
        """
        Cliente aceita horário sugerido → APPROVED.

        R4-F6 (parada de escritas ``Schedule`` em paths ativos / ADR-024
        sunset): não cria mais ``Schedule`` — bookings novos são sempre
        core-only (``CoreBooking``, sem ``Schedule`` associado) desde
        R3-F2, e ``DisponibilidadeService``/``core_bookings`` é quem
        valida conflito de horário (fonte primária desde R4-F4). O model
        ``Schedule`` é mantido (sem DROP — ver ``docs/sprints/R4-F6.md``/
        ``docs/sprints/R4-F7.md``; R4-F7 removeu a FK física de
        ``Schedule.agendamento_id`` para ``agendamentos.id``, DROP físico
        do model adiado para R4-F8), só deixa de receber escrita nova
        por este caminho. Método permanece ativo apenas para transição de
        status de ``Agendamento`` legado histórico ainda em
        ``WAITING_TIME_CONFIRMATION`` (sem router HTTP associado — ver
        ``ScheduleService.criar_para_reserva`` para o path equivalente
        removido; reagendamento core-only ainda não tem endpoint
        ``/v1/bookings`` dedicado, débito residual documentado no gate
        R4-F6).

        Args:
            reservation_id: ID da reserva.

        Returns:
            Reserva aprovada.
        """
        ag = self.obter(reservation_id)
        if ag.status != ReservationStatus.WAITING_TIME_CONFIRMATION:
            raise BusinessRuleError("Nenhum reagendamento pendente")
        if not ag.horario_sugerido:
            raise BusinessRuleError("Horário sugerido não definido")

        ag.data_hora = ag.horario_sugerido
        ag.horario_aprovado = ag.horario_sugerido
        ag.status = ReservationStatus.APPROVED
        self.db.commit()

        logger.info(
            "aceitar_reagendamento id=%s não cria Schedule (R4-F6 — parada de "
            "escrita legado); disponibilidade validada via core_bookings/v1 bookings",
            reservation_id,
        )
        return self.obter(reservation_id)

    def cancelar(self, reservation_id: int, motivo: Optional[str] = None) -> Agendamento:
        """
        **Removido em R3-F2** — cancelamento de reserva via legado.

        Antes cancelava a reserva e liberava o ``Schedule`` associado. Use
        ``POST /v1/bookings/{id}/cancel`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo opcional.

        Returns:
            Nunca retorna — sempre levanta exceção.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def concluir(self, reservation_id: int) -> Agendamento:
        """
        Marca atendimento como concluído → COMPLETED.

        Args:
            reservation_id: ID da reserva.

        Returns:
            Reserva concluída.
        """
        ag = self.obter(reservation_id)
        ag.status = ReservationStatus.COMPLETED
        self.schedule.concluir(reservation_id)
        self.db.commit()

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_atendimento_concluido(reservation_id)
        return self.obter(reservation_id)

    def registrar_pagamento_final(
        self,
        reservation_id: int,
        transaction_id: Optional[str] = None,
    ) -> Agendamento:
        """
        Confirma pagamento final → PAID.

        Args:
            reservation_id: ID da reserva.
            transaction_id: ID da transação.

        Returns:
            Reserva paga.
        """
        self.payments.confirmar_pagamento_final(reservation_id, transaction_id)
        ag = self.obter(reservation_id)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_pagamento_final(reservation_id)
        return ag
