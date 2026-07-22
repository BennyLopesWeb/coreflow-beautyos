"""
Service de Reservas (Reservation) — deprecado (R4-F8).

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida via DROP físico (ADR-024
    sunset / RFC-003 M11+ — ver ``docs/sprints/R4-F8.md``). R3-F2 já havia
    removido os métodos de **escrita do booking** (``criar``,
    ``criar_de_schema``, ``aprovar``, ``rejeitar``, ``cancelar`` — sempre
    levantam ``BusinessRuleError`` apontando para ``/v1/bookings``); esta
    release remove também a capacidade de **leitura** (``listar``,
    ``obter`` e os métodos que dependem deles) — a tabela não existe mais
    fisicamente. As assinaturas e DocStrings são mantidas por
    compatibilidade de referência/import; ``QueueEntryService`` (fallback
    legado em ``checkin``/``iniciar``/``concluir``) e o router
    ``/payments/final`` continuam chamando este service, mas agora sempre
    recebem ``NotFoundError`` para IDs legado (nenhuma reserva legado pode
    mais existir).
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.models.agendamento import ReservationStatus
from app.schemas.reservation import ReservationCreate
from app.core.exceptions import NotFoundError, BusinessRuleError
from app.services.payment_reservation_service import PaymentReservationService
from app.core.logging_config import get_logger

logger = get_logger("reservation_service")


class ReservationService:
    """
    Orquestra reservas legado — todos os métodos de leitura/transição de
    estado são no-ops desde a remoção física da tabela ``agendamentos``
    (R4-F8); os de escrita já eram bloqueados desde R3-F2.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy.
        """
        self.db = db
        self.payments = PaymentReservationService(db)

    def listar(
        self,
        status: Optional[ReservationStatus] = None,
        cliente_id: Optional[int] = None,
        data_ref: Optional[datetime] = None,
        pendentes: bool = False,
        company_id: Optional[int] = None,
    ) -> List:
        """
        Lista reservas legado com filtros opcionais.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — sempre retorna lista vazia.

        Args:
            status: Ignorado.
            cliente_id: Ignorado.
            data_ref: Ignorado.
            pendentes: Ignorado.
            company_id: Ignorado.

        Returns:
            Lista vazia.
        """
        return []

    def obter(self, reservation_id: int):
        """
        Obtém reserva legado por ID.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida (DROP físico R4-F8) — sempre
            levanta ``NotFoundError``.

        Args:
            reservation_id: ID da reserva legado.

        Raises:
            NotFoundError: Sempre — a tabela não existe mais.
        """
        raise NotFoundError("Reserva", str(reservation_id))

    def criar(
        self,
        cliente_id: int,
        tranca_id: int,
        service_image_id: int,
        data_hora: datetime,
        observacoes: Optional[str] = None,
    ):
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

    def criar_de_schema(self, data: ReservationCreate, company_id: Optional[int] = None):
        """
        **Removido em R3-F2** — criação de reserva via legado.

        Antes criava ``Agendamento`` com snapshot de preço/duração/sinal do
        modelo e publicava ``reservation.created``. O booking write path
        legado foi removido (ADR-027/ADR-033/RFC-003 M4) — use
        ``POST /v1/bookings`` (flag ``booking.core.enabled``). O dual-write
        outbound que existia a partir do path core (``project_create_booking``)
        foi removido definitivamente em R4-F3 — bookings são sempre
        core-only. Desde R4-F8 a tabela ``agendamentos`` nem existe mais
        fisicamente.

        Args:
            data: Dados validados.
            company_id: Tenant BeautyOS (herdado da categoria se omitido).

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
    ):
        """
        Confirma pagamento do sinal → PENDING_APPROVAL.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter``, que sempre levanta
            ``NotFoundError``. Use
            ``PaymentReservationService.confirmar_deposito_por_booking``.

        Args:
            reservation_id: ID da reserva legado.
            transaction_id: Ignorado.
            comprovante_url: Ignorado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter(reservation_id)

    def aprovar(self, reservation_id: int):
        """
        **Removido em R3-F2** — aprovação de reserva via legado.

        Use ``POST /v1/bookings/{id}/approve`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def rejeitar(self, reservation_id: int, motivo: str):
        """
        **Removido em R3-F2** — rejeição de reserva via legado.

        Use ``POST /v1/bookings/{id}/reject`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo da rejeição.

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
    ):
        """
        Admin sugere novo horário → WAITING_TIME_CONFIRMATION.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter``, que sempre levanta
            ``NotFoundError``. Use
            ``POST /v1/bookings/{id}/reschedule`` (R4-F11 / ADR-026).

        Args:
            reservation_id: ID da reserva legado.
            novo_horario: Ignorado.
            mensagem: Ignorado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter(reservation_id)

    def aceitar_reagendamento(self, reservation_id: int):
        """
        Cliente aceita horário sugerido → APPROVED.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter``, que sempre levanta
            ``NotFoundError``.

        Args:
            reservation_id: ID da reserva legado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter(reservation_id)

    def cancelar(self, reservation_id: int, motivo: Optional[str] = None):
        """
        **Removido em R3-F2** — cancelamento de reserva via legado.

        Antes cancelava a reserva e liberava o ``Schedule`` associado. Use
        ``POST /v1/bookings/{id}/cancel`` (ADR-027/ADR-033/RFC-003 M4).

        Args:
            reservation_id: ID da reserva.
            motivo: Motivo opcional.

        Raises:
            BusinessRuleError: Sempre — use ``/v1/bookings``.
        """
        raise BusinessRuleError(
            "Legacy booking write removed (R3-F2) — use /v1/bookings"
        )

    def concluir(self, reservation_id: int):
        """
        Marca atendimento como concluído → COMPLETED.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter``, que sempre levanta
            ``NotFoundError``. Chamado por
            ``QueueEntryService.concluir`` apenas no fallback legado
            (``entry.agendamento_id`` sem ``booking_id``), que nunca mais
            ocorre para entradas criadas após R4-F3.

        Args:
            reservation_id: ID da reserva legado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter(reservation_id)

    def registrar_pagamento_final(
        self,
        reservation_id: int,
        transaction_id: Optional[str] = None,
    ):
        """
        Confirma pagamento final → PAID.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter``, que sempre levanta
            ``NotFoundError``. Não há ainda endpoint core-only
            equivalente para pagamento final (débito residual — ver
            ``docs/sprints/R4-F8.md``).

        Args:
            reservation_id: ID da reserva legado.
            transaction_id: Ignorado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter(reservation_id)
