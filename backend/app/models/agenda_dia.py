"""
Model AgendaDia
Configuração de expediente por data para a profissional.
"""
from sqlalchemy import Column, Integer, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class AgendaDia(Base):
    """
    Configuração de agenda para um dia específico.

    Permite definir horário de início/fim e se o dia está ativo.
    Quando não há registro, usa-se o expediente padrão (08:00–18:00).
    """
    __tablename__ = "agenda_dias"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    data = Column(Date, nullable=False, index=True)
    hora_inicio = Column(Integer, default=8, nullable=False)
    minuto_inicio = Column(Integer, default=0, nullable=False)
    hora_fim = Column(Integer, default=18, nullable=False)
    minuto_fim = Column(Integer, default=0, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
