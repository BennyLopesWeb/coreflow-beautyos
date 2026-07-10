"""
ORM IdempotencyKey — dedupe de POST mutating (ADR-031).
"""
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class IdempotencyKey(Base):
    """
    Registro de resposta idempotente por tenant e endpoint.

    Attributes:
        id: PK interna.
        idempotency_key: UUID v4 enviado pelo cliente (header).
        company_id: Tenant.
        endpoint: Rota lógica (ex.: POST /v1/bookings).
        request_hash: SHA-256 do body normalizado.
        response_status: HTTP status da resposta original (201 ou 200).
        response_body: JSON serializado da resposta cacheada.
        booking_id: FK lógica core_bookings.id quando aplicável.
        expires_at: TTL 24h — ADR-031.
        created_at: Timestamp de criação.
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            "company_id",
            "endpoint",
            name="uq_idempotency_key_company_endpoint",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(64), nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    endpoint = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False, default=201)
    response_body = Column(Text, nullable=False)
    booking_id = Column(Integer, nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
