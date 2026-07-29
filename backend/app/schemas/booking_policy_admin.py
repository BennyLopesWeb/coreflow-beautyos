"""
Schemas HTTP da API administrativa de política de booking (FIX-CONFIG-02).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BookingPolicyAdminResponse(BaseModel):
    """
    Resposta da política de booking do tenant autenticado.

    Attributes:
        company_id: Tenant efetivo da autenticação (próprio, nunca cross-tenant).
        has_active_override: Se existe override ativo persistido.
        source: Origem dominante da política efetiva (``default`` ou ``override``).
        policy: Documento efetivo resolvido (defaults + override validado).
        override: Documento de override persistido, se ativo; senão ``None``.
        version: Versão do override ativo, se houver.
        updated_at: Última atualização do override ativo, se houver.
    """

    model_config = ConfigDict(extra="forbid")

    company_id: int
    has_active_override: bool
    source: Literal["default", "override"]
    policy: Dict[str, Any]
    override: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    updated_at: Optional[datetime] = None


class BookingPolicyOverrideRequest(BaseModel):
    """
    Payload de create/update de override (PUT/PATCH).

    Aceita documento parcial alinhado ao schema ``BookingPolicy``.
    Não aceita ``company_id`` nem chaves arbitrárias no topo além dos
    grupos canônicos — a validação definitiva ocorre via ``merge_and_validate``.

    Attributes:
        expiration: Patch do grupo expiração.
        cancellation: Patch do grupo cancelamento.
        reversal_cancelled: Patch de reversão de cancelado.
        reversal_expired: Patch de reversão de expirado.
        manual_status: Patch de status manual.
        activation: Patch do grupo de entrada mínima.
        expected_version: Versão otimista do override ativo (409 se divergir).
        reason: Motivo obrigatório para auditoria.
    """

    model_config = ConfigDict(extra="forbid")

    expiration: Optional[Dict[str, Any]] = None
    cancellation: Optional[Dict[str, Any]] = None
    reversal_cancelled: Optional[Dict[str, Any]] = None
    reversal_expired: Optional[Dict[str, Any]] = None
    manual_status: Optional[Dict[str, Any]] = None
    activation: Optional[Dict[str, Any]] = None
    expected_version: Optional[int] = Field(default=None, ge=1)
    reason: str = Field(..., min_length=1, max_length=500)

    def to_override_dict(self) -> Dict[str, Any]:
        """
        Extrai o documento de override sem metadados de auditoria/concorrência.

        Returns:
            Dict apenas com grupos de política presentes no payload.
        """
        data = self.model_dump(
            exclude_none=True,
            exclude={"reason", "expected_version"},
        )
        return data
