"""
Model ServiceImage
Representa uma imagem de um serviço (trança)
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class ServiceImage(Base):
    """
    Model de Imagem de Serviço
    Armazena URLs de imagens associadas a um serviço
    """
    __tablename__ = "service_images"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("trancas.id"), nullable=False, index=True)
    url = Column(String(255), nullable=False)  # URL da imagem
    ordem = Column(Integer, default=0, nullable=False)  # Ordem de exibição
    is_principal = Column(Boolean, default=False, nullable=False)  # Imagem principal
    nome = Column(String(255), nullable=True)  # Nome do modelo (ex: Box Braids Premium)
    descricao = Column(String(255), nullable=True)  # Descrição do modelo
    nivel_complexidade = Column(String(20), nullable=True)  # baixa, media, alta
    valor_total = Column(Numeric(10, 2), nullable=True)
    valor_sinal = Column(Numeric(10, 2), nullable=True)
    percentual_sinal = Column(Numeric(5, 4), nullable=True, default=0.30)
    duracao_minutos = Column(Integer, nullable=True)
    quantidade_trancas = Column(Integer, nullable=True)
    quantidade_cabelo = Column(String(50), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamento
    service = relationship("Tranca", backref="images")

