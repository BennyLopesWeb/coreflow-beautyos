"""
Model SatisfactionSurvey
Representa uma pesquisa de satisfação
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Integer as SQLInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class SatisfactionSurvey(Base):
    """
    Model de Pesquisa de Satisfação
    Armazena respostas de pesquisas de satisfação dos clientes
    """
    __tablename__ = "satisfaction_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    
    # Avaliações (1-5)
    nota_atendimento = Column(SQLInteger, nullable=True)  # 1-5
    nota_qualidade = Column(SQLInteger, nullable=True)  # 1-5
    nota_pontualidade = Column(SQLInteger, nullable=True)  # 1-5
    nota_geral = Column(SQLInteger, nullable=False)  # 1-5
    
    # Feedback
    comentario = Column(Text, nullable=True)
    recomendaria = Column(String, nullable=True)  # sim, não, talvez
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    agendamento = relationship("Agendamento", backref="surveys")
    cliente = relationship("Cliente", backref="surveys")

