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
            booking_id=entry.booking_id,
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

        R4-F4 (hard sunset / ADR-024 / RFC-003 M8): ``core_bookings`` é a
        fonte primária — a maioria das reservas aprovadas desde R3-F2/R4-F3
        não tem mais linha em ``agendamentos``. Processa ambas as fontes
        (``core_bookings`` primário + ``agendamentos`` histórico) sem
        duplicar quando um booking core ainda possui ``legacy_agendamento_id``
        (histórico dual-write anterior a R4-F3).

        Returns:
            Quantidade total processada (core + histórico).
        """
        hoje = date.today()
        inicio = datetime.combine(hoje, time.min)
        fim = datetime.combine(hoje, time.max)

        count = self._processar_agendamentos_legado_do_dia(hoje, inicio, fim)
        count += self._processar_core_bookings_do_dia(hoje, inicio, fim)
        return count

    def _processar_agendamentos_legado_do_dia(
        self, hoje: date, inicio: datetime, fim: datetime
    ) -> int:
        """
        Processa reservas legado (``agendamentos``) aprovadas para hoje.

        Mantido para reservas históricas criadas antes de R3-F2/R4-F3 (dados
        antigos com dual-write ainda ativo); nenhum caminho de escrita atual
        cria novas linhas em ``agendamentos``.

        Args:
            hoje: Data de referência (hoje).
            inicio: Início do dia.
            fim: Fim do dia.

        Returns:
            Quantidade de ``QueueEntry`` criadas a partir de ``agendamentos``.
        """
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

    def _processar_core_bookings_do_dia(
        self, hoje: date, inicio: datetime, fim: datetime
    ) -> int:
        """
        Processa ``core_bookings`` APPROVED de hoje → IN_QUEUE + QueueEntry (R4-F4).

        Path primário desde R4-F4: bookings core-only (sem
        ``legacy_agendamento_id``, criados via ``CreateBookingHandler``) não
        aparecem na consulta legado acima, então precisam ser processados
        aqui para entrar na fila operacional do dia. Bookings que ainda têm
        ``legacy_agendamento_id`` preenchido (histórico de dual-write
        anterior a R4-F3) são ignorados aqui — já foram cobertos pela
        consulta a ``agendamentos``.

        Resolve ``tranca_id``/``service_image_id`` legado via
        ``catalog_id``/``offering_id`` (ACL) apenas para preencher os campos
        de exibição da fila — não é necessária nova linha em
        ``agendamentos`` para o vínculo (``QueueEntry.agendamento_id``
        permanece ``None`` para bookings core-only).

        R4-F5: a entrada criada aqui recebe ``booking_id=booking.id`` (FK
        forte para ``core_bookings``), usado por ``checkin``/``iniciar``/
        ``concluir`` para avançar o status do booking core diretamente,
        sem depender da heurística por atributos compostos usada apenas
        para dedupe (evitar processar o mesmo booking duas vezes).

        Args:
            hoje: Data de referência (hoje).
            inicio: Início do dia.
            fim: Fim do dia.

        Returns:
            Quantidade de ``QueueEntry`` criadas a partir de ``core_bookings``.
        """
        from app.modules.booking.domain.models import CoreBooking

        bookings = self.db.query(CoreBooking).filter(
            CoreBooking.scheduled_at >= inicio,
            CoreBooking.scheduled_at <= fim,
            CoreBooking.status == ReservationStatus.APPROVED,
            CoreBooking.deleted_at.is_(None),
        ).all()

        count = 0
        for booking in bookings:
            if booking.legacy_agendamento_id:
                # Já coberto por _processar_agendamentos_legado_do_dia.
                continue

            tranca_id = booking.catalog.legacy_tranca_id if booking.catalog else None
            service_image_id = booking.offering.legacy_service_image_id if booking.offering else None
            horario_entrada = booking.scheduled_at.time() if booking.scheduled_at else None

            existente = (
                self.db.query(QueueEntry)
                .filter(
                    (QueueEntry.booking_id == booking.id)
                    | (
                        (QueueEntry.booking_id.is_(None))
                        & (QueueEntry.cliente_id == booking.customer_id)
                        & (QueueEntry.data == hoje)
                        & (QueueEntry.tranca_id == tranca_id)
                        & (QueueEntry.service_image_id == service_image_id)
                        & (QueueEntry.horario_entrada == horario_entrada)
                    )
                )
                .first()
            )
            if existente:
                continue

            posicao = self._proxima_posicao(hoje)
            entry = QueueEntry(
                agendamento_id=None,
                booking_id=booking.id,
                cliente_id=booking.customer_id,
                tranca_id=tranca_id,
                service_image_id=service_image_id,
                posicao=posicao,
                data=hoje,
                horario_entrada=horario_entrada,
                status=QueueEntryStatus.WAITING,
                observacoes=booking.notes,
                mesmo_dia=0,
            )
            booking.status = ReservationStatus.IN_QUEUE
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

    def _avancar_booking_core(self, entry: QueueEntry, novo_status: ReservationStatus) -> None:
        """
        Avança o status do ``CoreBooking`` vinculado à entrada (R4-F5).

        Fecha o gap operacional identificado no gate R4-F4: entradas
        core-only (sem ``agendamento_id``, o caso mais comum desde
        R4-F3/R4-F4) não avançavam o booking core durante o atendimento.
        Atualização direta via ORM (sem ``BookingDomainService``, que hoje
        só cobre create/approve/reject/cancel — não modela os estados
        operacionais IN_QUEUE/CHECKED_IN/IN_SERVICE/COMPLETED).

        Args:
            entry: Entrada da fila operacional já com ``booking_id``
                resolvido (chamada é um no-op silencioso se ``None``).
            novo_status: Novo ``ReservationStatus`` para o ``CoreBooking``.

        Returns:
            None. A alteração é apenas adicionada à sessão — o commit é
            responsabilidade do chamador.
        """
        if not entry.booking_id:
            return
        from app.modules.booking.domain.models import CoreBooking

        booking = self.db.query(CoreBooking).filter(CoreBooking.id == entry.booking_id).first()
        if booking:
            booking.status = novo_status

    def checkin(self, entry_id: int) -> QueueEntry:
        """
        Cliente fez check-in.

        R4-F5: se a entrada tiver ``booking_id`` (core-only ou core+legado),
        avança ``CoreBooking.status`` para ``CHECKED_IN`` também. Entradas
        legado puras (``agendamento_id`` preenchido, sem ``booking_id`` —
        histórico anterior à migração) continuam atualizando apenas
        ``Agendamento``.

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.CHECKED_IN
        if entry.booking_id:
            self._avancar_booking_core(entry, ReservationStatus.CHECKED_IN)
        elif entry.agendamento_id:
            ag = self.db.query(Agendamento).filter(Agendamento.id == entry.agendamento_id).first()
            if ag:
                ag.status = ReservationStatus.CHECKED_IN
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def iniciar(self, entry_id: int) -> QueueEntry:
        """
        Inicia atendimento (IN_SERVICE).

        R4-F5: se a entrada tiver ``booking_id``, avança
        ``CoreBooking.status`` para ``IN_SERVICE`` também (mesma regra de
        precedência de ``checkin`` — booking core primeiro, fallback para
        ``Agendamento`` legado apenas quando não há ``booking_id``).

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.IN_SERVICE
        if entry.booking_id:
            self._avancar_booking_core(entry, ReservationStatus.IN_SERVICE)
        elif entry.agendamento_id:
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

        R4-F5: para entradas com ``booking_id`` (core-only), avança
        ``CoreBooking.status`` para ``COMPLETED`` diretamente — o
        pagamento final de bookings core-only já é tratado por
        ``PaymentReservationService``/``POST /admin/pagamentos/booking/...``
        (não há ``Schedule``/``Payment`` legado associado a migrar aqui;
        essa migração fica para R4-F6). Entradas legado puras (sem
        ``booking_id``) continuam delegando a ``ReservationService.concluir``
        (que também aciona ``Schedule`` e notificação legado).

        Args:
            entry_id: ID da entrada.

        Returns:
            QueueEntry atualizado.
        """
        entry = self._obter(entry_id)
        entry.status = QueueEntryStatus.COMPLETED

        if entry.booking_id:
            self._avancar_booking_core(entry, ReservationStatus.COMPLETED)
        elif entry.agendamento_id:
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
        Aprova fila urgente criando booking core vinculado (R3-F3 / R4-F2).

        Resolve catalog/offering via ACL e delega a ``CreateBookingHandler``
        (mesmo padrão de ``PromoteWaitlistHandler``).

        R4-F3 (ADR-024 sunset / dual-write outbound removido definitivamente):
        o booking criado é sempre core-only — ``booking.legacy_agendamento_id``
        vem ``None`` e ``entry.agendamento_id`` é deixado ``None`` (sem
        levantar erro; não há mais projeção legado).

        R4-F5: ``entry.booking_id`` é sempre preenchido com o ``id`` do
        booking core criado, independente de haver projeção legado — é
        esse vínculo que ``checkin``/``iniciar``/``concluir`` usam para
        avançar ``CoreBooking.status`` durante o atendimento.

        Args:
            entry_id: ID da entrada.
            data_hora: Horário confirmado.

        Returns:
            QueueEntry atualizado com ``booking_id`` do booking core criado
            e ``agendamento_id`` da projeção legado quando presente
            (``None`` para booking core-only).

        Raises:
            BusinessRuleError: Entrada sem modelo definido.
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

        # CreateBookingHandler já faz commit — recarrega entry e vincula
        entry = self._obter(entry_id)
        entry.agendamento_id = booking.legacy_agendamento_id
        entry.booking_id = booking.id
        entry.status = QueueEntryStatus.WAITING
        self.db.commit()
        self.db.refresh(entry)
        return entry
