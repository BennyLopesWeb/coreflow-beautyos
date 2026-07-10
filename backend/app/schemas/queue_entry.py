"""
Schemas da fila operacional (QueueEntry).
"""
from pydantic import BaseModel
from datetime import date, datetime, time
from typing import Optional, List
from app.models.queue_entry import QueueEntryStatus


class QueueJoinRequest(BaseModel):
    """Entrada na fila (urgente / mesmo dia)."""
    cliente_id: int
    tranca_id: int
    service_image_id: int
    observacoes: Optional[str] = None
    mesmo_dia: bool = True


class QueueEntryResponse(BaseModel):
    """Item da fila operacional."""
    id: int
    agendamento_id: Optional[int] = None
    cliente_id: int
    cliente_nome: str
    tranca_nome: Optional[str] = None
    modelo_nome: Optional[str] = None
    posicao: int
    data: date
    horario_entrada: Optional[time] = None
    status: QueueEntryStatus
    observacoes: Optional[str] = None
    mesmo_dia: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QueueResumoResponse(BaseModel):
    """Fila do dia."""
    data: date
    total: int
    entries: List[QueueEntryResponse]
