"""
Model Fila
Fila de espera para atendimentos sem horário confirmado.
"""
from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey, String, Boolean, Enum as SQLEnum, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class StatusFila(str, enum.Enum):
    """Status de um item na fila de espera."""
    WAITING = "waiting"
    CONTACTED = "contacted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


# Status ativos na fila (participam do FIFO)
STATUS_FILA_ATIVOS = (
    StatusFila.WAITING,
    StatusFila.CONTACTED,
)


class Fila(Base):
    """
    Fila de espera virtual.

    Cliente entra sem horário confirmado; a profissional aprova manualmente
    e, ao aprovar, cria-se a reserva efetiva vinculada.

    R4-F7: ``agendamento_id`` deixou de ter FK física para
    ``agendamentos.id`` (permanece ``Integer`` simples, sem constraint) —
    ``booking_id`` (FK ``core_bookings.id``, desde R4-F5) é o vínculo
    autoritativo.
    """
    __tablename__ = "fila"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    tranca_id = Column(Integer, ForeignKey("trancas.id"), nullable=False, index=True)
    service_image_id = Column(Integer, ForeignKey("service_images.id"), nullable=False, index=True)
    data = Column(Date, nullable=False, index=True)
    horario_desejado = Column(Time, nullable=True)
    observacoes = Column(String(255), nullable=True)
    mesmo_dia = Column(Boolean, default=False, nullable=False)
    posicao = Column(Integer, nullable=False)
    status = Column(SQLEnum(StatusFila), default=StatusFila.WAITING, nullable=False, index=True)
    # R4-F7: FK física para agendamentos.id removida — Integer simples,
    # mantido apenas para leitura histórica. unique=True preservado (nulls
    # múltiplos permitidos).
    agendamento_id = Column(Integer, nullable=True, unique=True)
    # R4-F5: FK para core_bookings.id — vínculo forte criado por aprovar_fila,
    # substituindo a dependência exclusiva de legacy_agendamento_id (sempre
    # None para bookings core-only desde R4-F3/R4-F4).
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cliente = relationship("Cliente", backref="filas")
    tranca = relationship("Tranca", backref="filas")
    service_image = relationship("ServiceImage", backref="filas")
