"""
Schemas de Agendamento
DTOs para validação e serialização de agendamentos
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.agendamento import StatusAgendamento, StatusPagamento


class AgendamentoBase(BaseModel):
    """Schema base de agendamento"""
    cliente_id: int
    tranca_id: int
    data_hora: datetime
    observacoes: Optional[str] = None


class AgendamentoCreate(AgendamentoBase):
    """Schema para criação de agendamento sobre um modelo específico"""
    service_image_id: int


class AgendamentoUpdate(BaseModel):
    """Schema para atualização de agendamento"""
    data_hora: Optional[datetime] = None
    status: Optional[StatusAgendamento] = None
    observacoes: Optional[str] = None


class AgendamentoResponse(AgendamentoBase):
    """Schema de resposta de agendamento com valores persistidos da reserva"""
    id: int
    sinal_pago: bool
    comprovante_url: Optional[str] = None
    service_image_id: Optional[int] = None
    modelo_nome: Optional[str] = None
    imagem_url: Optional[str] = None
    imagem_label: Optional[str] = None
    valor_total_reserva: Optional[Decimal] = None
    valor_sinal_reserva: Optional[Decimal] = None
    valor_restante_reserva: Optional[Decimal] = None
    duracao_reserva_minutos: Optional[int] = None
    status_pagamento: StatusPagamento
    status: StatusAgendamento
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisponibilidadeRequest(BaseModel):
    """Schema para consulta de disponibilidade"""
    data: datetime
    tranca_id: int


class HorarioDisponivel(BaseModel):
    """Schema de horário disponível"""
    horario: datetime
    disponivel: bool


class DisponibilidadeResponse(BaseModel):
    """Schema de resposta de disponibilidade"""
    data: datetime
    tranca_id: int
    horarios: List[HorarioDisponivel]
