"""
Model Schedule
Bloco de agenda vinculado a uma reserva aprovada.
"""
from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class ScheduleStatus(str, enum.Enum):
    """Status de um bloco na agenda."""
    SCHEDULED = "scheduled"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Schedule(Base):
    """
    Representa ocupação de horário na agenda da profissional.

    Criado quando reserva é aprovada; usado para detectar conflitos.

    R4-F7 (decouple físico das FKs restantes para ``agendamentos`` / ADR-024
    sunset / RFC-003 M11): ``agendamento_id`` deixou de ter FK física para
    ``agendamentos.id`` (permanece ``Integer`` simples, preenchido apenas
    para schedules históricos) e passou a ser nullable — ``booking_id``
    (FK nullable ``core_bookings.id``) é o novo vínculo autoritativo, mesmo
    padrão adotado em ``Payment`` no R4-F6. Nenhum caminho de escrita ativo
    cria ``Schedule`` novo (``ScheduleService.criar_para_reserva`` está sem
    call-site desde R4-F6); model mantido — sem DROP — até **R4-F8**.
    """
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    # R4-F7: FK física para agendamentos.id removida — Integer simples,
    # mantido apenas para leitura histórica. unique=True preservado (nulls
    # múltiplos permitidos).
    agendamento_id = Column(Integer, nullable=True, unique=True, index=True)
    # R4-F7: FK para core_bookings.id — vínculo autoritativo para schedules
    # de bookings core-only (sem Agendamento associado). Nullable para
    # preservar compatibilidade com schedules históricos ligados apenas a
    # agendamento_id.
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    data = Column(Date, nullable=False, index=True)
    inicio = Column(DateTime(timezone=True), nullable=False)
    fim = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        SQLEnum(ScheduleStatus),
        default=ScheduleStatus.SCHEDULED,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
