"""
Model NotificationLog
Representa um log de notificação enviada
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class NotificationType(str, enum.Enum):
    """Tipo de notificação"""
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    """Status da notificação"""
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    FALHA = "falha"
    CANCELADA = "cancelada"


class NotificationLog(Base):
    """
    Model de Log de Notificação
    Armazena histórico de notificações enviadas

    R4-F7: ``agendamento_id`` deixou de ter FK física para
    ``agendamentos.id`` (permanece ``Integer`` simples, opcional, sem
    constraint) — mantido apenas para leitura histórica.
    """
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    # R4-F7: FK física para agendamentos.id removida — Integer simples.
    agendamento_id = Column(Integer, nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    
    # Informações da notificação
    tipo = Column(SQLEnum(NotificationType), nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDENTE, nullable=False)
    destinatario = Column(String(255), nullable=False)  # Telefone, email, etc
    mensagem = Column(Text, nullable=True)  # Conteúdo da mensagem
    
    # Metadados
    tentativas = Column(Integer, default=0, nullable=False)
    erro = Column(String(255), nullable=True)  # Mensagem de erro se falhou
    
    # Timestamps
    enviada_at = Column(DateTime(timezone=True), nullable=True)  # Quando foi enviada
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="notifications")

