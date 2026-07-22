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

    R4-F7 (decouple físico das FKs restantes para ``agendamentos`` / ADR-024
    sunset / RFC-003 M11): ``agendamento_id`` deixou de ter FK física para
    ``agendamentos.id`` (permanece ``Integer`` simples, sem constraint) e
    passou a ser nullable — ``booking_id`` (FK nullable ``core_bookings.id``)
    é o novo vínculo para pesquisas associadas a bookings core-only. Não há
    service/router ativo criando ``SatisfactionSurvey`` nesta release
    (débito residual documentado — ver ``docs/sprints/R4-F7.md``); model
    mantido — sem DROP — até **R4-F8**.
    """
    __tablename__ = "satisfaction_surveys"
    
    id = Column(Integer, primary_key=True, index=True)
    # R4-F7: FK física para agendamentos.id removida — Integer simples,
    # mantido apenas para leitura histórica.
    agendamento_id = Column(Integer, nullable=True, index=True)
    # R4-F7: FK para core_bookings.id — vínculo para pesquisas associadas a
    # bookings core-only (sem Agendamento associado).
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    
    # Avaliações (1-5)
    nota_atendimento = Column(SQLInteger, nullable=True)  # 1-5
    nota_qualidade = Column(SQLInteger, nullable=True)  # 1-5
    nota_pontualidade = Column(SQLInteger, nullable=True)  # 1-5
    nota_geral = Column(SQLInteger, nullable=False)  # 1-5
    
    # Feedback
    comentario = Column(Text, nullable=True)
    recomendaria = Column(String(255), nullable=True)  # sim, não, talvez
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    cliente = relationship("Cliente", backref="surveys")

