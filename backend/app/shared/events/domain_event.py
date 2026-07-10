"""
Eventos de domínio compartilhados — base Event-Driven Architecture v3.0.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
import uuid


@dataclass(frozen=True)
class DomainEvent:
    """
    Evento de domínio imutável publicado por um bounded context.

    Attributes:
        event_id: Identificador único do evento (idempotência / audit).
        event_type: Nome do tipo (ex.: reservation.created).
        occurred_at: Timestamp UTC da ocorrência.
        company_id: Tenant BeautyOS associado ao evento.
        payload: Dados serializáveis do evento.
        aggregate_id: ID da entidade raiz (opcional).
        aggregate_type: Tipo da entidade raiz (opcional).
    """

    event_type: str
    company_id: int
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str | None = None
    aggregate_type: str | None = None
    correlation_id: str | None = None
