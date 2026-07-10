"""
Model Financeiro
Representa movimentações financeiras
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class TipoMovimento(str, enum.Enum):
    """Tipo de movimento financeiro"""
    ENTRADA = "entrada"
    SAIDA = "saida"


class Financeiro(Base):
    """
    Model de Movimento Financeiro
    Armazena entradas e saídas financeiras
    """
    __tablename__ = "financeiro"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    tipo = Column(SQLEnum(TipoMovimento), nullable=False, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=True)  # Opcional
    data = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamento
    agendamento = relationship("Agendamento", backref="movimentos_financeiros")

