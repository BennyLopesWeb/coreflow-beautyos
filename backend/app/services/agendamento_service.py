"""
Service de Agendamento — deprecado (R4-F8).

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida via DROP físico (ADR-024
    sunset / RFC-003 M11+ — ver ``docs/sprints/R4-F8.md``). Nenhum método
    deste service consulta mais a tabela: leitura retorna sempre vazio/
    ``NotFoundError`` e escrita continua bloqueada (``criar_agendamento``,
    desde R4-F4). Mantido apenas por compatibilidade de referência/import
    — os call-sites de produção (``core_bookings``/``CoreBooking``) não
    dependem mais deste service.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.schemas.agendamento import AgendamentoCreate, AgendamentoUpdate
from app.core.exceptions import NotFoundError, BusinessRuleError


class AgendamentoService:
    """
    Service legado de agendamentos — todos os métodos são no-ops desde a
    remoção física da tabela ``agendamentos`` (R4-F8).
    """

    def __init__(self, db: Session):
        """
        Args:
            db: Sessão SQLAlchemy (não utilizada — mantida por
                compatibilidade de assinatura).
        """
        self.db = db

    def listar_agendamentos(self) -> List:
        """
        Lista agendamentos legado.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — sempre retorna lista vazia.

        Returns:
            Lista vazia.
        """
        return []

    def buscar_por_id(self, agendamento_id: int) -> Optional[object]:
        """
        Busca agendamento legado por ID.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — sempre retorna ``None``.

        Args:
            agendamento_id: ID legado (ignorado).

        Returns:
            None.
        """
        return None

    def obter_agendamento(self, agendamento_id: int):
        """
        Obtém agendamento legado por ID.

        .. deprecated:: 2.11.0-r4-f8
            Tabela ``agendamentos`` removida (DROP físico R4-F8) — sempre
            levanta ``NotFoundError``. Use ``core_bookings``
            (``POST /v1/bookings`` e derivados) para reservas atuais.

        Args:
            agendamento_id: ID legado.

        Raises:
            NotFoundError: Sempre — a tabela não existe mais.
        """
        raise NotFoundError("Agendamento", str(agendamento_id))

    def criar_agendamento(self, agendamento_data: AgendamentoCreate):
        """
        [DESATIVADO — R4-F4 hard sunset / R4-F8 DROP físico] Bloqueia
        criação de novas linhas em ``agendamentos``.

        Toda escrita de reserva passa por ``CreateBookingHandler``
        (``POST /v1/bookings``), que persiste em ``core_bookings`` (SoT).
        Desde R4-F8 a tabela ``agendamentos`` nem existe mais fisicamente.

        Args:
            agendamento_data: Dados que seriam usados para criar a reserva
                (ignorados).

        Raises:
            BusinessRuleError: Sempre. Aponta o chamador para
                ``POST /v1/bookings``.
        """
        raise BusinessRuleError(
            "Criação de agendamento legado foi desativada em R4-F4 (hard sunset) "
            "e a tabela foi removida em R4-F8. Use POST /v1/bookings "
            "(CreateBookingHandler) — core_bookings é a fonte da verdade "
            "para novas reservas."
        )

    def confirmar_sinal(self, agendamento_id: int):
        """
        Confirma pagamento do sinal de uma reserva legado.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter_agendamento``, que sempre
            levanta ``NotFoundError``. Use
            ``PaymentReservationService.confirmar_deposito_por_booking``.

        Args:
            agendamento_id: ID legado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter_agendamento(agendamento_id)

    def aprovar_reserva(self, agendamento_id: int):
        """
        Aprova reserva legado após pagamento do sinal.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter_agendamento``, que sempre
            levanta ``NotFoundError``. Use
            ``POST /v1/bookings/{id}/approve``.

        Args:
            agendamento_id: ID legado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter_agendamento(agendamento_id)

    def atualizar_agendamento(
        self,
        agendamento_id: int,
        agendamento_data: AgendamentoUpdate,
    ):
        """
        Atualiza agendamento legado existente.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter_agendamento``, que sempre
            levanta ``NotFoundError``.

        Args:
            agendamento_id: ID legado.
            agendamento_data: Dados de atualização (ignorados).

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter_agendamento(agendamento_id)

    def cancelar_agendamento(
        self,
        agendamento_id: int,
        liberar_vaga: bool = True,
        motivo: Optional[str] = None,
    ):
        """
        Cancela agendamento legado.

        .. deprecated:: 2.11.0-r4-f8
            Tabela removida — delega a ``obter_agendamento``, que sempre
            levanta ``NotFoundError``. Use
            ``POST /v1/bookings/{id}/cancel``.

        Args:
            agendamento_id: ID legado.
            liberar_vaga: Ignorado.
            motivo: Ignorado.

        Raises:
            NotFoundError: Sempre.
        """
        return self.obter_agendamento(agendamento_id)
