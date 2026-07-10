"""
Model Cliente
Representa um cliente do sistema
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Cliente(Base):
    """
    Model de Cliente
    Armazena informações dos clientes do sistema
    """
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    nome = Column(String, nullable=False, index=True)
    telefone = Column(String, unique=True, nullable=False, index=True)  # Telefone único
    email = Column(String, nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

