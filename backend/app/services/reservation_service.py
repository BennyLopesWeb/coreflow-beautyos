"""
Service de Reservas (Reservation).
Ciclo completo: criar, pagar sinal, aprovar, rejeitar, reagendar, concluir.
"""
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento, STATUS_OCUPAM_VAGA
from app.models.payment import PaymentType
from app.models.tranca import Tranca
from app.schemas.reservation import ReservationCreate
from app.core.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.service_image_service import ServiceImageService
from app.services.schedule_service import ScheduleService
from app.services.payment_reservation_service import PaymentReservationService
from app.utils.service_image_precos import resolver_precos_imagem, calcular_sinal
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
        Cria reserva com snapshot de preço/duração/sinal do modelo.

        Args:
            cliente_id: ID do cliente.
            tranca_id: ID da categoria.
            service_image_id: ID do modelo.
            data_hora: Horário solicitado.
            observacoes: Notas opcionais.

        Returns:
            Reserva criada (PENDING_PAYMENT).
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
        Cria reserva a partir do schema.

        Args:
            data: Dados validados.
            company_id: Tenant BeautyOS (herdado da categoria se omitido).

        Returns:
            Reserva persistida.
        """
        if data.data_hora < datetime.now():
            raise ValidationError("Não é possível reservar no passado")

        tranca = self.db.query(Tranca).filter(Tranca.id == data.tranca_id).first()
        if not tranca or not tranca.ativo:
            raise BusinessRuleError("Categoria inválida ou inativa")

        resolved_company_id = company_id or tranca.company_id

        self.images.validar_imagem_da_tranca(data.tranca_id, data.service_image_id)
        img = self.images.obter_imagem(data.service_image_id)
        precos = resolver_precos_imagem(img)

        horarios = self.disponibilidade.calcular_horarios_disponiveis(
            data.data_hora, data.tranca_id, data.service_image_id
        )
        if not any(h.horario == data.data_hora and h.disponivel for h in horarios):
            raise BusinessRuleError("Horário não disponível")

        duracao = precos["duracao_minutos"]
        fim = data.data_hora + timedelta(minutes=duracao)
        if self.schedule.tem_conflito(data.data_hora, fim):
            raise BusinessRuleError("Conflito de horário na agenda")

        pct = Decimal(str(img.percentual_sinal or "0.30"))
        valor_total = Decimal(str(precos["valor_total"]))
        valor_sinal = Decimal(str(precos["valor_sinal"]))
        valor_restante = Decimal(str(precos["valor_restante"]))

        ag = Agendamento(
            company_id=resolved_company_id,
            cliente_id=data.cliente_id,
            tranca_id=data.tranca_id,
            service_image_id=data.service_image_id,
            data_hora=data.data_hora,
            valor_total=valor_total,
            percentual_sinal=pct,
            valor_sinal=valor_sinal,
            valor_restante=valor_restante,
            observacoes=data.observacoes,
            status=ReservationStatus.PENDING_PAYMENT,
            status_pagamento=StatusPagamento.PENDING_PAYMENT,
            sinal_pago=False,
        )
        self.db.add(ag)
        self.db.flush()
        self.db.refresh(ag)

        self.payments.criar_pendente(ag.id, PaymentType.DEPOSIT, valor_sinal)

        from app.modules.booking.domain.events import reservation_created
        from app.shared.events.outbox import OutboxService

        if resolved_company_id:
            OutboxService(self.db).record_and_publish(
                reservation_created(
                    company_id=resolved_company_id,
                    reservation_id=ag.id,
                    cliente_id=ag.cliente_id,
                    valor_sinal=str(valor_sinal),
                )
            )

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_nova_reserva(ag.id)

        self.db.commit()
        self.db.refresh(ag)

        return self.obter(ag.id)

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
        Admin aprova reserva → APPROVED + Schedule.

        Args:
            reservation_id: ID da reserva.

        Returns:
            Reserva aprovada.
        """
        ag = self.obter(reservation_id)
        if not ag.sinal_pago:
            raise BusinessRuleError("Sinal não pago")
        if ag.status not in (
            ReservationStatus.PENDING_APPROVAL,
            ReservationStatus.WAITING_TIME_CONFIRMATION,
        ):
            raise BusinessRuleError("Reserva não está aguardando aprovação")

        ag.status = ReservationStatus.APPROVED
        ag.horario_aprovado = ag.horario_sugerido or ag.data_hora
        self.db.commit()

        self.schedule.criar_para_reserva(ag)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_reserva_aprovada(reservation_id)
        return self.obter(reservation_id)

    def rejeitar(self, reservation_id: int, motivo: str) -> Agendamento:
        """
        Admin rejeita reserva.

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo da rejeição.

        Returns:
            Reserva rejeitada.
        """
        ag = self.obter(reservation_id)
        ag.status = ReservationStatus.REJECTED
        ag.motivo_rejeicao = motivo
        self.schedule.cancelar(reservation_id)
        self.db.commit()

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_reserva_rejeitada(reservation_id, motivo)
        return self.obter(reservation_id)

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

        self.schedule.criar_para_reserva(ag)
        return self.obter(reservation_id)

    def cancelar(self, reservation_id: int, motivo: Optional[str] = None) -> Agendamento:
        """
        Cancela reserva e libera schedule.

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo opcional.

        Returns:
            Reserva cancelada.
        """
        ag = self.obter(reservation_id)
        ag.status = ReservationStatus.CANCELLED
        ag.status_pagamento = StatusPagamento.CANCELLED
        ag.deleted_at = datetime.utcnow()
        if motivo:
            ag.observacoes = (ag.observacoes or "") + f" | {motivo}"
        self.schedule.cancelar(reservation_id)
        self.db.commit()
        self.db.refresh(ag)
        return ag

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
