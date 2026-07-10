"""
Model QueueEntry
Fila operacional do dia do atendimento (pós-aprovação).
"""
from sqlalchemy import Column, Integer, Date, DateTime, Time, ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class QueueEntryStatus(str, enum.Enum):
    """Status operacional na fila de atendimento."""
    WAITING = "waiting"
    CALLED = "called"
    CHECKED_IN = "checked_in"
    IN_SERVICE = "in_service"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


STATUS_FILA_OPERACIONAL_ATIVOS = (
    QueueEntryStatus.WAITING,
    QueueEntryStatus.CALLED,
    QueueEntryStatus.CHECKED_IN,
    QueueEntryStatus.IN_SERVICE,
)


class QueueEntry(Base):
    """
    Entrada na fila operacional do salão.

    Diferente de Fila (waitlist pré-reserva): aqui o cliente já tem reserva aprovada
    ou entrou para atendimento urgente no mesmo dia.
    """
    __tablename__ = "queue_entries"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    tranca_id = Column(Integer, ForeignKey("trancas.id"), nullable=True)
    service_image_id = Column(Integer, ForeignKey("service_images.id"), nullable=True)
    posicao = Column(Integer, nullable=False)
    data = Column(Date, nullable=False, index=True)
    horario_entrada = Column(Time, nullable=True)
    status = Column(
        SQLEnum(QueueEntryStatus),
        default=QueueEntryStatus.WAITING,
        nullable=False,
        index=True,
    )
    observacoes = Column(String, nullable=True)
    mesmo_dia = Column(Integer, default=0, nullable=False)  # 0/1 flag urgente
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agendamento = relationship("Agendamento", backref="queue_entry", uselist=False)
    cliente = relationship("Cliente", backref="queue_entries")
    tranca = relationship("Tranca", backref="queue_entries")
    service_image = relationship("ServiceImage", backref="queue_entries")
