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
    """
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    agendamento_id = Column(
        Integer, ForeignKey("agendamentos.id"), nullable=False, unique=True, index=True
    )
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

    agendamento = relationship("Agendamento", backref="schedule", uselist=False)
