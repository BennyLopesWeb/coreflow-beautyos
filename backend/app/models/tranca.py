"""
Model Tranca
Representa um estilo de trança oferecido
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Tranca(Base):
    """
    Model de Tranca
    Armazena informações dos estilos de trança disponíveis
    """
    __tablename__ = "trancas"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    # Campos legados — não usar em regras de negócio (preço/duração ficam no modelo)
    duracao_minutos = Column(Integer, nullable=True)
    valor_total = Column(Numeric(10, 2), nullable=True)
    valor_sinal = Column(Numeric(10, 2), nullable=True)
    imagens = Column(JSON, default=list)  # Imagem(ns) de capa da categoria
    ativo = Column(Boolean, default=True, nullable=False)  # Se está ativo no catálogo
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

