"""
Model Agendamento (Reservation) — enums + stub deprecado.

.. deprecated:: 2.11.0-r4-f8
    **DROP físico executado (R4-F8 / ADR-024 sunset / RFC-003 M11+).** A
    tabela ``agendamentos`` foi removida via
    ``alembic/versions/cf016_r4_f8_drop_agendamentos.py`` — nenhuma
    consulta/escrita de produção deve mais depender dela. A classe
    ``Agendamento`` **deixou de ser um model SQLAlchemy** (não herda mais
    ``Base``, não tem ``__tablename__``/``Column``) nesta release — é
    mantida apenas como stub para compatibilidade de referência/import
    (alguns módulos ainda importam o símbolo por herança histórica). Usar
    ``self.db.query(Agendamento)`` levanta erro imediatamente (classe não
    mapeada) — todos os call-sites de produção foram migrados para
    ``core_bookings``/``CoreBooking`` (ver ``app.modules.booking.domain.models``)
    ou convertidos em no-ops documentados (ver ``docs/sprints/R4-F8.md``).

    Os enums abaixo (``ReservationStatus``, ``StatusPagamento``,
    ``StatusAgendamento``, ``STATUS_OCUPAM_VAGA``) **continuam em uso** —
    são compartilhados por ``CoreBooking.status``/``CoreBooking.payment_status``
    e por várias colunas históricas (``payments``, ``fila``, ``schedules``
    etc.) que armazenam esses valores como ``Integer``/``String`` simples,
    sem depender da tabela removida.
"""
import enum


class ReservationStatus(str, enum.Enum):
    """
    Status completo do ciclo de vida da reserva.

    Aliases legados mantidos para compatibilidade com dados existentes.
    """
    PENDING_PAYMENT = "pending_payment"
    PENDING_APPROVAL = "pending_approval"
    WAITING_TIME_CONFIRMATION = "waiting_time_confirmation"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_QUEUE = "in_queue"
    CHECKED_IN = "checked_in"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"
    PAID = "paid"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"  # R4-F11 / ADR-026 — substituído por novo booking
    # Legado
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    CONCLUIDO = "concluido"
    NO_SHOW = "no_show"


# Status que bloqueiam slot na agenda
STATUS_OCUPAM_VAGA = (
    ReservationStatus.PENDING_PAYMENT,
    ReservationStatus.PENDING_APPROVAL,
    ReservationStatus.APPROVED,
    ReservationStatus.IN_QUEUE,
    ReservationStatus.CHECKED_IN,
    ReservationStatus.IN_SERVICE,
    # Legado
    ReservationStatus.PENDENTE,
    ReservationStatus.CONFIRMADO,
)

# Alias para código existente
StatusAgendamento = ReservationStatus


class StatusPagamento(str, enum.Enum):
    """Status de pagamento agregado da reserva."""
    PENDING_PAYMENT = "pending_payment"
    PARTIALLY_PAID = "partially_paid"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PAID = "paid"


class Agendamento:
    """
    Stub deprecado — tabela ``agendamentos`` removida em R4-F8.

    .. deprecated:: 2.11.0-r4-f8
        Não é mais um model SQLAlchemy (sem ``Base``/``__tablename__``).
        Mantido apenas para import de referência histórica em docstrings
        e assinaturas de função que ainda mencionam o tipo. **Não deve
        ser instanciado nem usado em ``session.query(...)``** — isso
        levanta erro imediatamente, já que a classe não está mapeada.
    """
