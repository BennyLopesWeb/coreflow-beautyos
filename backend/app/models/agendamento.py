"""
Model Agendamento (Reservation)
Representa uma reserva de serviço sobre um modelo específico.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base
from app.db.enum_column import enum_values


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


class Agendamento(Base):
    """
    Reserva persistida no banco (tabela agendamentos).

    Toda informação comercial vem do snapshot do modelo (service_image).
    """
    __tablename__ = "agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    tranca_id = Column(Integer, ForeignKey("trancas.id"), nullable=False, index=True)
    service_image_id = Column(Integer, ForeignKey("service_images.id"), nullable=False, index=True)
    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    horario_aprovado = Column(DateTime(timezone=True), nullable=True)
    sinal_pago = Column(Boolean, default=False, nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)
    percentual_sinal = Column(Numeric(5, 4), nullable=False, default=0.30)
    valor_sinal = Column(Numeric(10, 2), nullable=False)
    valor_restante = Column(Numeric(10, 2), nullable=False)
    status_pagamento = Column(
        enum_values(StatusPagamento),
        default=StatusPagamento.PENDING_PAYMENT,
        nullable=False,
    )
    comprovante_url = Column(String, nullable=True)
    status = Column(
        enum_values(ReservationStatus),
        default=ReservationStatus.PENDING_PAYMENT,
        nullable=False,
        index=True,
    )
    observacoes = Column(String, nullable=True)
    motivo_rejeicao = Column(Text, nullable=True)
    horario_sugerido = Column(DateTime(timezone=True), nullable=True)
    mensagem_reagendamento = Column(Text, nullable=True)
    google_calendar_event_id = Column(String, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    cliente = relationship("Cliente", backref="agendamentos")
    tranca = relationship("Tranca", backref="agendamentos")
    service_image = relationship("ServiceImage", backref="agendamentos")
