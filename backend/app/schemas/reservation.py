"""
Schemas de Reserva (Reservation).
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.agendamento import ReservationStatus, StatusPagamento


class ReservationCreate(BaseModel):
    """Criação de reserva sobre modelo específico."""
    cliente_id: int
    tranca_id: int
    service_image_id: int
    data_hora: datetime = Field(..., description="Data/hora solicitada")
    observacoes: Optional[str] = None


class ReservationUpdate(BaseModel):
    """Atualização parcial."""
    data_hora: Optional[datetime] = None
    observacoes: Optional[str] = None


class ReservationResponse(BaseModel):
    """Resposta completa da reserva."""
    id: int
    cliente_id: int
    tranca_id: int
    service_image_id: int
    data_hora: datetime
    horario_aprovado: Optional[datetime] = None
    valor_total: Decimal
    percentual_sinal: Decimal
    valor_sinal: Decimal
    valor_restante: Decimal
    sinal_pago: bool
    status_pagamento: StatusPagamento
    status: ReservationStatus
    observacoes: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    horario_sugerido: Optional[datetime] = None
    mensagem_reagendamento: Optional[str] = None
    comprovante_url: Optional[str] = None
    cliente_nome: Optional[str] = None
    tranca_nome: Optional[str] = None
    modelo_nome: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservationRejectRequest(BaseModel):
    """Rejeição de reserva."""
    motivo: str


class ReservationRescheduleRequest(BaseModel):
    """Solicitação de ajuste de horário."""
    novo_horario: datetime
    mensagem: Optional[str] = None


class ReservationAcceptRescheduleRequest(BaseModel):
    """Cliente aceita novo horário proposto."""
    aceitar: bool = True
