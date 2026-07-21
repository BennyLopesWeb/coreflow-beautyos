"""
Service de fila operacional (QueueEntry).
"""
from sqlalchemy.orm import Session
from datetime import datetime, date, time
from typing import List, Optional

from app.models.queue_entry import QueueEntry, QueueEntryStatus, STATUS_FILA_OPERACIONAL_ATIVOS
from app.models.agendamento import Agendamento, ReservationStatus
from app.models.cliente import Cliente
from app.models.tranca import Tranca
from app.models.service_image import ServiceImage
from app.schemas.queue_entry import QueueJoinRequest, QueueEntryResponse
from app.core.exceptions import NotFoundError, BusinessRuleError, ValidationError


class QueueEntryService:
    """
    Fila operacional do dia: call, check-in, in-service, complete.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db

    def _proxima_posicao(self, data_ref: date) -> int:
        """
        Calcula próxima posição FIFO.

        Args:
            data_ref: Data da fila.

        Returns:
            Próximo número de posição.
        """
        ultima = (
            self.db.query(QueueEntry)
            .filter(
                QueueEntry.data == data_ref,
                QueueEntry.status.in_(STATUS_FILA_OPERACIONAL_ATIVOS),
            )
            .order_by(QueueEntry.posicao.desc())
            .first()
        )
        return (ultima.posicao + 1) if ultima else 1

    def _enriquecer(self, entry: QueueEntry) -> QueueEntryResponse:
        """
        Converte QueueEntry em resposta enriquecida.

        Args:
            entry: Registro da fila.

        Returns:
            QueueEntryResponse.
        """
        from app.schemas.service_image import _label_modelo

        cliente = self.db.query(Cliente).filter(Cliente.id == entry.cliente_id).first()
        tranca = self.db.query(Tranca).filter(Tranca.id == entry.tranca_id).first() if entry.tranca_id else None
        img = (
            self.db.query(ServiceImage).filter(ServiceImage.id == entry.service_image_id).first()
            if entry.service_image_id else None
        )
        return QueueEntryResponse(
            id=entry.id,
            agendamento_id=entry.agendamento_id,
            cliente_id=entry.cliente_id,
            cliente_nome=cliente.nome if cliente else "Cliente",
            tranca_nome=tranca.nome if tranca else None,
            modelo_nome=_label_modelo(img) if img else None,
            posicao=entry.posicao,
            data=entry.data,
            horario_entrada=entry.horario_entrada,
            status=entry.status,
            observacoes=entry.observacoes,
            mesmo_dia=bool(entry.mesmo_dia),
            created_at=entry.created_at,
        )

    def entrar(self, dados: QueueJoinRequest) -> QueueEntry:
        """
        Cliente entra na fila operacional (urgente / mesmo dia).

        Args:
            dados: Dados da entrada.

        Returns:
            QueueEntry criado.
        """
        hoje = date.today()
        posicao = self._proxima_posicao(hoje)
        company_id = getattr(dados, "company_id", None) or 1
        entry = QueueEntry(
            company_id=company_id,
            cliente_id=dados.cliente_id,
            tranca_id=dados.tranca_id,
            service_image_id=dados.service_image_id,
            posicao=posicao,
            data=hoje,
            horario_entrada=datetime.now().time(),
            status=QueueEntryStatus.WAITING,
            observacoes=dados.observacoes,
            mesmo_dia=1 if dados.mesmo_dia else 0,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_entrada_fila_operacional(entry.id)
        return entry

    def processar_reservas_do_dia(self) -> int:
        """
        Rotina diária: reservas APPROVED de hoje → IN_QUEUE + QueueEntry.

        Returns:
            Quantidade processada.
        """
        hoje = date.today()
        inicio = datetime.combine(hoje, time.min)
        fim = datetime.combine(hoje, time.max)

        reservas = self.db.query(Agendamento).filter(
            Agendamento.data_hora >= inicio,
            Agendamento.data_hora <= fim,
            Agendamento.status.in_([ReservationStatus.APPROVED, ReservationStatus.CONFIRMADO]),
            Agendamento.deleted_at.is_(None),
        ).all()

        count = 0
        for ag in reservas:
            existente = (
                self.db.query(QueueEntry)
                .filter(QueueEntry.agendamento_id == ag.id)
                .first()
            )
            if existente:
                continue
            posicao = self._proxima_posicao(hoje)
            entry = QueueEntry(
                agendamento_id=ag.id,
                cliente_id=ag.cliente_id,
                tranca_id=ag.tranca_id,
                service_image_id=ag.service_image_id,
                posicao=posicao,
                data=hoje,
                horario_entrada=ag.data_hora.time() if ag.data_hora else None,
                status=QueueEntryStatus.WAITING,
                observacoes=ag.observacoes,
                mesmo_dia=0,
            )
            ag.status = ReservationStatus.IN_QUEUE
            self.db.add(entry)
            count += 1

        if count:
            self.db.commit()
        return count

    def listar(self, data_ref: Optional[date] = None) -> List[QueueEntryResponse]:
        """
        Lista fila operacional do dia (FIFO).

        Args:
            data_ref: Data; default hoje.

        Returns:
            Lista enriquecida.
        """
        data_ref = data_ref or date.today()
        entries = (
            self.db.query(QueueEntry)
            .filter(
                QueueEntry.data == data_ref,
                QueueEntry.status.in_(STATUS_FILA_OPERACIONAL_ATIVOS + (QueueEntryStatus.COMPLETED,)),
            )
            .order_by(QueueEntry.posicao)
            .all()
        )
        return [self._enriquecer(e) for e in entries if e.status != QueueEntryStatus.COMPLETED]

    def _obter(self, entry_id: int) -> QueueEntry:
        """
        Obtém entrada ou lança NotFoundError.

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry.
        """
        entry = self.db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
        if not entry:
            raise NotFoundError("Fila operacional", str(entry_id))
        return entry

    def chamar(self, entry_id: int) -> QueueEntry:
        """
        Admin chama cliente (CALLED).

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.CALLED
        self.db.commit()
        self.db.refresh(entry)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_cliente_chamado(entry.id)
        return entry

    def checkin(self, entry_id: int) -> QueueEntry:
        """
        Cliente fez check-in.

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.CHECKED_IN
        if entry.agendamento_id:
            ag = self.db.query(Agendamento).filter(Agendamento.id == entry.agendamento_id).first()
            if ag:
                ag.status = ReservationStatus.CHECKED_IN
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def iniciar(self, entry_id: int) -> QueueEntry:
        """
        Inicia atendimento (IN_SERVICE).

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.IN_SERVICE
        if entry.agendamento_id:
            ag = self.db.query(Agendamento).filter(Agendamento.id == entry.agendamento_id).first()
            if ag:
                ag.status = ReservationStatus.IN_SERVICE
        self.db.commit()
        self.db.refresh(entry)

        from app.services.notification_service import NotificationService
        NotificationService(self.db).notificar_atendimento_iniciado(entry.agendamento_id)
        return entry

    def concluir(self, entry_id: int) -> QueueEntry:
        """
        Finaliza atendimento e dispara pagamento final.

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.COMPLETED

        if entry.agendamento_id:
            from app.services.reservation_service import ReservationService
            ReservationService(self.db).concluir(entry.agendamento_id)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def cancelar(self, entry_id: int) -> QueueEntry:
        """
        Cancela entrada na fila.

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry cancelado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.CANCELLED
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def aprovar_com_horario(self, entry_id: int, data_hora: datetime) -> QueueEntry:
        """
        Aprova fila urgente criando booking core vinculado (R3-F3).

        Resolve catalog/offering via ACL e delega a ``CreateBookingHandler``
        (mesmo padrão de ``PromoteWaitlistHandler``).

        Args:
            entry_id: ID da entrada.
            data_hora: Horário confirmado.

        Returns:
            QueueEntry atualizado com ``agendamento_id`` da projeção legado.

        Raises:
            BusinessRuleError: Entrada sem modelo ou mapeamento catalog ausente.
            ValidationError: Mapeamento catalog/offering inválido.
        """
        from app.modules.booking.application.commands.create_booking import (
            CreateBookingCommand,
            CreateBookingHandler,
        )
        from app.shared.acl.catalog_port import LegacyCatalogAdapter

        entry = self._obter(entry_id)
        if not entry.tranca_id or not entry.service_image_id:
            raise BusinessRuleError("Entrada sem modelo definido")

        company_id = entry.company_id or 1
        catalog_acl = LegacyCatalogAdapter(self.db)
        catalog = catalog_acl.resolve_catalog_by_legacy_tranca(
            entry.tranca_id, company_id
        )
        offering = catalog_acl.resolve_offering_by_legacy_image(
            entry.service_image_id, company_id
        )
        if not catalog or not offering:
            raise ValidationError(
                "Catalog/offering não sincronizados para tranca/modelo da fila — "
                "execute sync catalog antes de aprovar"
            )

        scheduled_at = data_hora.replace(tzinfo=None) if data_hora.tzinfo else data_hora
        booking_result = CreateBookingHandler(self.db).execute(
            CreateBookingCommand(
                customer_id=entry.cliente_id,
                catalog_id=catalog.id,
                offering_id=offering.id,
                scheduled_at=scheduled_at,
                company_id=company_id,
                notes=entry.observacoes,
            )
        )
        booking = booking_result.booking
        if not booking.legacy_agendamento_id:
            raise BusinessRuleError("Booking criado sem projeção legado (agendamento_id)")

        # CreateBookingHandler já faz commit — recarrega entry e vincula
        entry = self._obter(entry_id)
        entry.agendamento_id = booking.legacy_agendamento_id
        entry.status = QueueEntryStatus.WAITING
        self.db.commit()
        self.db.refresh(entry)
        return entry
