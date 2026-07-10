"""
IdempotencyStore — port + adapter SQLAlchemy (ADR-031 / ADR-025).
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.shared.idempotency.models import IdempotencyKey

BOOKING_CREATE_ENDPOINT = "POST /v1/bookings"
IDEMPOTENCY_TTL_HOURS = 24


@dataclass(frozen=True)
class IdempotencyCachedResult:
    """
    Resposta idempotente previamente persistida.

    Args:
        booking_id: ID core_bookings.
        response_status: HTTP status original.
        response_body: Dict deserializado da resposta.
        request_hash: Hash do body original.
    """

    booking_id: int
    response_status: int
    response_body: Dict[str, Any]
    request_hash: str


class IdempotencyStore:
    """
    Persistência e lookup de chaves idempotentes.

    Args:
        db: Sessão SQLAlchemy ativa na mesma TX do handler.
    """

    def __init__(self, db: Session):
        self.db = db

    def check(
        self,
        idempotency_key: str,
        company_id: int,
        endpoint: str,
        request_hash: str,
    ) -> Optional[IdempotencyCachedResult]:
        """
        Busca registro válido (não expirado) para a chave.

        Args:
            idempotency_key: Header Idempotency-Key.
            company_id: Tenant.
            endpoint: Rota lógica.
            request_hash: Hash do body atual.

        Returns:
            IdempotencyCachedResult se existir e não expirado; None caso contrário.

        Raises:
            ValueError: Mesma chave com body diferente (caller mapeia para 409).
        """
        now = datetime.utcnow()
        row = (
            self.db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.company_id == company_id,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.expires_at > now,
            )
            .first()
        )
        if not row:
            ArchitectureMetricsStore.get().record_idempotency_miss()
            return None

        if row.request_hash != request_hash:
            ArchitectureMetricsStore.get().record_idempotency_conflict()
            raise ValueError("idempotency_key_reused")

        ArchitectureMetricsStore.get().record_idempotency_hit()
        return IdempotencyCachedResult(
            booking_id=row.booking_id,
            response_status=row.response_status,
            response_body=json.loads(row.response_body),
            request_hash=row.request_hash,
        )

    def save(
        self,
        idempotency_key: str,
        company_id: int,
        endpoint: str,
        request_hash: str,
        response_status: int,
        response_body: Dict[str, Any],
        booking_id: Optional[int] = None,
    ) -> IdempotencyKey:
        """
        Persiste snapshot de resposta na TX corrente (flush, sem commit).

        Args:
            idempotency_key: Header Idempotency-Key.
            company_id: Tenant.
            endpoint: Rota lógica.
            request_hash: Hash do body.
            response_status: HTTP status (201 na primeira execução).
            response_body: Corpo JSON-serializável da resposta.
            booking_id: ID booking criado.

        Returns:
            Registro IdempotencyKey persistido.

        Raises:
            ValueError: Conflito de hash em race (idempotency_key_reused).
        """
        expires_at = datetime.utcnow() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)
        row = IdempotencyKey(
            idempotency_key=idempotency_key,
            company_id=company_id,
            endpoint=endpoint,
            request_hash=request_hash,
            response_status=response_status,
            response_body=json.dumps(response_body, default=str),
            booking_id=booking_id,
            expires_at=expires_at,
        )
        nested = self.db.begin_nested()
        try:
            self.db.add(row)
            self.db.flush()
        except IntegrityError as exc:
            nested.rollback()
            cached = self.check(idempotency_key, company_id, endpoint, request_hash)
            if cached:
                return row
            raise ValueError("idempotency_key_reused") from exc
        return row
