"""
Service de Agendamento
Lógica de negócio para gerenciamento de agendamentos
"""
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal
from app.models.agendamento import Agendamento, ReservationStatus, StatusAgendamento, StatusPagamento, STATUS_OCUPAM_VAGA
from app.models.cliente import Cliente
from app.models.tranca import Tranca
from app.schemas.agendamento import AgendamentoCreate, AgendamentoUpdate
from app.core.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.financeiro_service import FinanceiroService
from app.integrations.google_calendar import GoogleCalendarService
from app.integrations.whatsapp import WhatsAppService
from app.core.logging_config import get_logger

logger = get_logger("agendamento_service")


def _chave_slot(data_hora: datetime) -> tuple:
    """
    Normaliza datetime para comparação de slot (data + hora + minuto).

    Args:
        data_hora: Data/hora com ou sem timezone.

    Returns:
        Tupla (ano, mês, dia, hora, minuto).
    """
    if data_hora.tzinfo is not None:
        data_hora = data_hora.replace(tzinfo=None)
    return (data_hora.year, data_hora.month, data_hora.day, data_hora.hour, data_hora.minute)


class AgendamentoService:
    """
    Service para gerenciamento de agendamentos
    Centraliza todas as regras de negócio relacionadas a agendamentos
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.disponibilidade_service = DisponibilidadeService(db)
        self.financeiro_service = FinanceiroService(db)
        self.google_calendar = GoogleCalendarService()
        self.whatsapp = WhatsAppService()
    
    def listar_agendamentos(self) -> List[Agendamento]:
        """Lista todos os agendamentos (não deletados)"""
        return (
            self.db.query(Agendamento)
            .options(
                joinedload(Agendamento.service_image),
                joinedload(Agendamento.tranca),
            )
            .filter(Agendamento.deleted_at.is_(None))
            .order_by(Agendamento.data_hora)
            .all()
        )
    
    def buscar_por_id(self, agendamento_id: int) -> Optional[Agendamento]:
        """Busca agendamento por ID (não deletado)"""
        return (
            self.db.query(Agendamento)
            .options(
                joinedload(Agendamento.service_image),
                joinedload(Agendamento.tranca),
            )
            .filter(
                Agendamento.id == agendamento_id,
                Agendamento.deleted_at.is_(None),
            )
            .first()
        )
    
    def obter_agendamento(self, agendamento_id: int) -> Agendamento:
        """
        Obtém agendamento por ID
        Lança exceção se não encontrado
        """
        agendamento = self.buscar_por_id(agendamento_id)
        if not agendamento:
            raise NotFoundError("Agendamento", str(agendamento_id))
        return agendamento
    
    def criar_agendamento(self, agendamento_data: AgendamentoCreate) -> Agendamento:
        """
        Cria novo agendamento
        Valida todas as regras de negócio antes de criar
        """
        # Validações básicas
        cliente = self.db.query(Cliente).filter(Cliente.id == agendamento_data.cliente_id).first()
        if not cliente:
            raise NotFoundError("Cliente", str(agendamento_data.cliente_id))
        
        tranca = self.db.query(Tranca).filter(Tranca.id == agendamento_data.tranca_id).first()
        if not tranca:
            raise NotFoundError("Trança", str(agendamento_data.tranca_id))
        
        if not tranca.ativo:
            raise BusinessRuleError("Trança não está ativa")
        
        # Validação: não permite agendamentos no passado
        if agendamento_data.data_hora < datetime.now():
            raise ValidationError("Não é possível agendar no passado")
        
        # Validação: verifica se horário está disponível (duração do modelo selecionado)
        horarios = self.disponibilidade_service.calcular_horarios_disponiveis(
            agendamento_data.data_hora,
            agendamento_data.tranca_id,
            agendamento_data.service_image_id,
        )
        
        chave_solicitada = _chave_slot(agendamento_data.data_hora)
        horario_valido = any(
            _chave_slot(h.horario) == chave_solicitada and h.disponivel
            for h in horarios
        )
        
        if not horario_valido:
            raise BusinessRuleError("Horário não está disponível")

        if self._tem_conflito_intervalo(
            agendamento_data.data_hora,
            agendamento_data.tranca_id,
            agendamento_data.service_image_id,
        ):
            raise BusinessRuleError("Horário já está ocupado")

        from app.services.service_image_service import ServiceImageService
        image_service = ServiceImageService(self.db)
        imagens = image_service.listar_por_tranca(agendamento_data.tranca_id)
        if not imagens:
            image_service.sincronizar_da_tranca(agendamento_data.tranca_id)
            imagens = image_service.listar_por_tranca(agendamento_data.tranca_id)
        if not imagens:
            raise ValidationError("Trança não possui fotos cadastradas")
        image_service.validar_imagem_da_tranca(
            agendamento_data.tranca_id,
            agendamento_data.service_image_id,
        )
        service_img = image_service.obter_imagem(agendamento_data.service_image_id)

        from app.utils.service_image_precos import resolver_precos_imagem
        try:
            precos = resolver_precos_imagem(service_img, tranca)
        except ValueError as e:
            raise ValidationError(str(e))

        agendamento = Agendamento(
            cliente_id=agendamento_data.cliente_id,
            tranca_id=agendamento_data.tranca_id,
            service_image_id=agendamento_data.service_image_id,
            data_hora=agendamento_data.data_hora,
            observacoes=agendamento_data.observacoes,
            status=ReservationStatus.PENDING_PAYMENT,
            sinal_pago=False,
            valor_total=precos["valor_total"],
            percentual_sinal=service_img.percentual_sinal or Decimal("0.30"),
            valor_sinal=precos["valor_sinal"],
            valor_restante=precos["valor_restante"],
            status_pagamento=StatusPagamento.PENDING_PAYMENT,
        )
        
        self.db.add(agendamento)
        self.db.commit()
        self.db.refresh(agendamento)
        agendamento.service_image = service_img
        agendamento.tranca = tranca

        from app.models.payment import PaymentType
        from app.services.payment_reservation_service import PaymentReservationService
        PaymentReservationService(self.db).criar_pendente(
            agendamento.id,
            PaymentType.DEPOSIT,
            precos["valor_sinal"],
        )

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_nova_reserva(agendamento.id)

        return agendamento

    def _tem_conflito_intervalo(
        self,
        data_hora: datetime,
        tranca_id: int,
        service_image_id: int,
        excluir_id: Optional[int] = None,
    ) -> bool:
        """
        Verifica sobreposição de intervalo com reservas ativas (capacidade única).

        Args:
            data_hora: Início do novo atendimento.
            tranca_id: Categoria (para duração do modelo).
            service_image_id: Modelo selecionado.
            excluir_id: ID a ignorar (atualização).

        Returns:
            True se houver conflito.
        """
        tranca = self.db.query(Tranca).filter(Tranca.id == tranca_id).first()
        if not tranca:
            return True
        duracao_nova = self.disponibilidade_service._duracao_minutos(tranca, service_image_id)
        fim_nova = data_hora + timedelta(minutes=duracao_nova)

        query = self.db.query(Agendamento).filter(
            Agendamento.status.in_(STATUS_OCUPAM_VAGA),
            Agendamento.deleted_at.is_(None),
        )
        if excluir_id:
            query = query.filter(Agendamento.id != excluir_id)

        for ag in query.all():
            duracao = self.disponibilidade_service._duracao_agendamento(ag)
            fim_existente = ag.data_hora + timedelta(minutes=duracao)
            if data_hora < fim_existente and fim_nova > ag.data_hora:
                return True
        return False
    
    def confirmar_sinal(self, agendamento_id: int) -> Agendamento:
        """
        Registra pagamento do sinal e move reserva para pending_approval.

        A confirmação definitiva (confirmado) exige aprovação manual da profissional.
        """
        logger.info(f"Confirmando pagamento do sinal - Agendamento ID: {agendamento_id}")

        agendamento = self.obter_agendamento(agendamento_id)

        if agendamento.sinal_pago:
            logger.warning(f"Tentativa de confirmar sinal já pago - Agendamento ID: {agendamento_id}")
            raise BusinessRuleError("Sinal já foi pago")

        agendamento.sinal_pago = True
        agendamento.status = StatusAgendamento.PENDING_APPROVAL
        agendamento.status_pagamento = StatusPagamento.PARTIALLY_PAID

        self.db.commit()
        self.db.refresh(agendamento)

        tranca = self.db.query(Tranca).filter(Tranca.id == agendamento.tranca_id).first()
        valor_sinal = agendamento.valor_sinal
        if valor_sinal is None and agendamento.service_image:
            from app.utils.service_image_precos import resolver_precos_imagem
            valor_sinal = resolver_precos_imagem(agendamento.service_image)["valor_sinal"]

        nome_servico = tranca.nome if tranca else "Trança"
        if agendamento.service_image:
            from app.schemas.service_image import _label_modelo
            nome_servico = f"{nome_servico} — {_label_modelo(agendamento.service_image)}"

        self.financeiro_service.registrar_entrada_automatica(
            descricao=f"Sinal - Agendamento #{agendamento.id} - {nome_servico}",
            valor=valor_sinal,
            agendamento_id=agendamento.id,
        )

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_reserva_aguardando_aprovacao(agendamento_id)

        logger.info(f"Sinal registrado, aguardando aprovação - Agendamento ID: {agendamento_id}")
        return agendamento

    def aprovar_reserva(self, agendamento_id: int) -> Agendamento:
        """
        Aprova reserva após pagamento do sinal (admin/profissional).

        Args:
            agendamento_id: ID da reserva.

        Returns:
            Agendamento confirmado.

        Raises:
            BusinessRuleError: Se status ou pagamento inválidos.
        """
        agendamento = self.obter_agendamento(agendamento_id)

        if not agendamento.sinal_pago:
            raise BusinessRuleError("Sinal ainda não foi pago")
        if agendamento.status != ReservationStatus.PENDING_APPROVAL:
            raise BusinessRuleError("Reserva não está aguardando aprovação")

        agendamento.status = ReservationStatus.APPROVED
        self.db.commit()
        self.db.refresh(agendamento)

        tranca = self.db.query(Tranca).filter(Tranca.id == agendamento.tranca_id).first()
        duracao = 60
        if agendamento.service_image:
            try:
                from app.utils.service_image_precos import resolver_precos_imagem
                duracao = resolver_precos_imagem(agendamento.service_image)["duracao_minutos"]
            except ValueError:
                duracao = agendamento.service_image.duracao_minutos or 60

        if tranca:
            fim_servico = agendamento.data_hora + timedelta(minutes=duracao)
            evento_id = self.google_calendar.criar_evento(
                titulo=f"Agendamento - {tranca.nome}",
                descricao=(
                    f"Cliente: {agendamento.cliente.nome}\n"
                    f"Trança: {tranca.nome}\n"
                    f"Observações: {agendamento.observacoes or 'Nenhuma'}"
                ),
                inicio=agendamento.data_hora,
                fim=fim_servico,
                email_cliente=agendamento.cliente.email,
                telefone_cliente=agendamento.cliente.telefone,
            )
            if evento_id:
                agendamento.google_calendar_event_id = evento_id
                self.db.commit()

        try:
            self.whatsapp.enviar_confirmacao_agendamento(
                telefone=agendamento.cliente.telefone,
                nome_cliente=agendamento.cliente.nome,
                data_hora=agendamento.data_hora,
                tipo_tranca=tranca.nome if tranca else "Trança",
            )
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp: {e}")

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_reserva_aprovada(agendamento_id)

        return agendamento
    
    def atualizar_agendamento(
        self,
        agendamento_id: int,
        agendamento_data: AgendamentoUpdate
    ) -> Agendamento:
        """
        Atualiza agendamento existente
        Valida regras antes de atualizar
        """
        agendamento = self.obter_agendamento(agendamento_id)
        
        update_data = agendamento_data.model_dump(exclude_unset=True)
        
        # Se mudou data/hora, valida disponibilidade
        if "data_hora" in update_data:
            nova_data_hora = update_data["data_hora"]
            if nova_data_hora < datetime.now():
                raise ValidationError("Não é possível agendar no passado")
            
            horarios = self.disponibilidade_service.calcular_horarios_disponiveis(
                nova_data_hora,
                agendamento.tranca_id,
                agendamento.service_image_id,
            )
            
            horario_valido = any(
                _chave_slot(h.horario) == _chave_slot(nova_data_hora) and h.disponivel
                for h in horarios
            )
            
            if not horario_valido:
                raise BusinessRuleError("Novo horário não está disponível")
        
        # Atualiza campos
        for key, value in update_data.items():
            setattr(agendamento, key, value)
        
        self.db.commit()
        self.db.refresh(agendamento)
        return agendamento
    
    def cancelar_agendamento(
        self,
        agendamento_id: int,
        liberar_vaga: bool = True,
        motivo: Optional[str] = None,
    ) -> Agendamento:
        """
        Cancela agendamento e opcionalmente sugere vaga liberada à fila.

        Args:
            agendamento_id: ID do agendamento.
            liberar_vaga: Se True, notifica primeiros da fila sobre vaga.
            motivo: Motivo do cancelamento (opcional).

        Returns:
            Agendamento cancelado.
        """
        agendamento = self.obter_agendamento(agendamento_id)

        if agendamento.status == StatusAgendamento.CANCELADO:
            raise BusinessRuleError("Agendamento já está cancelado")

        data_hora = agendamento.data_hora
        duracao = self.disponibilidade_service._duracao_agendamento(agendamento)

        agendamento.status = StatusAgendamento.CANCELADO
        agendamento.status_pagamento = StatusPagamento.CANCELLED
        agendamento.deleted_at = datetime.utcnow()
        if motivo:
            agendamento.observacoes = (agendamento.observacoes or "") + f" | Cancelado: {motivo}"

        self.db.commit()
        self.db.refresh(agendamento)

        if liberar_vaga:
            from app.services.fila_service import FilaService
            FilaService(self.db).sugerir_vaga_liberada(data_hora, duracao)

        return agendamento

