"""
Schemas de Fila de Espera
DTOs para validação e serialização da fila virtual.
"""
from pydantic import BaseModel, Field
from datetime import date, datetime, time
from typing import Optional, List
from app.models.fila import StatusFila


class FilaEsperaCreate(BaseModel):
    """Schema para entrada na fila de espera (sem horário confirmado)."""
    cliente_id: int
    tranca_id: int
    service_image_id: int
    data_desejada: date
    horario_desejado: Optional[time] = None
    observacoes: Optional[str] = None
    mesmo_dia: bool = False


class FilaResponse(BaseModel):
    """Schema de resposta de item da fila."""
    id: int
    cliente_id: int
    tranca_id: int
    service_image_id: int
    data: date
    horario_desejado: Optional[time] = None
    observacoes: Optional[str] = None
    mesmo_dia: bool
    posicao: int
    status: StatusFila
    agendamento_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FilaItemDetalhado(BaseModel):
    """Schema de item da fila com dados enriquecidos para exibição."""
    id: int
    posicao: int
    cliente_id: int
    cliente_nome: str
    cliente_telefone: str
    tranca_id: int
    tranca_nome: str
    service_image_id: int
    modelo_nome: str
    data: date
    horario_desejado: Optional[time] = None
    observacoes: Optional[str] = None
    mesmo_dia: bool
    status: StatusFila
    agendamento_id: Optional[int] = None
    created_at: datetime


class FilaResumoResponse(BaseModel):
    """Schema de resumo da fila do dia."""
    data: date
    total_pessoas: int
    posicoes: List[FilaItemDetalhado]


class FilaAtualizarStatusRequest(BaseModel):
    """Schema para alterar status de item da fila (admin)."""
    status: StatusFila


class FilaAprovarRequest(BaseModel):
    """Schema para aprovar item da fila e criar reserva."""
    data_hora: datetime = Field(..., description="Horário confirmado para a reserva")


class VagaSugeridaResponse(BaseModel):
    """Vaga liberada com sugestão para clientes da fila."""
    data_hora: datetime
    duracao_minutos: int
    fila_sugeridos: List[FilaItemDetalhado]
