"""
Schemas de configuração de agenda por dia.
"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


class AgendaDiaBase(BaseModel):
    """Configuração base de expediente para um dia."""
    data: date
    hora_inicio: int = Field(8, ge=0, le=23)
    minuto_inicio: int = Field(0, ge=0, le=59)
    hora_fim: int = Field(18, ge=0, le=23)
    minuto_fim: int = Field(0, ge=0, le=59)
    ativo: bool = True


class AgendaDiaCreate(AgendaDiaBase):
    """Schema para criar/atualizar configuração de um dia."""
    pass


class AgendaDiaResponse(AgendaDiaBase):
    """Resposta de configuração de agenda."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SlotAgendaItem(BaseModel):
    """Slot da agenda com status de disponibilidade."""
    horario: datetime
    disponivel: bool
    agendamento_id: Optional[int] = None
    cliente_nome: Optional[str] = None
    tranca_nome: Optional[str] = None
    status: Optional[str] = None


class AgendaDiaDetalheResponse(BaseModel):
    """Visão admin da agenda de um dia."""
    data: date
    hora_inicio: int
    minuto_inicio: int
    hora_fim: int
    minuto_fim: int
    ativo: bool
    slots: List[SlotAgendaItem]
