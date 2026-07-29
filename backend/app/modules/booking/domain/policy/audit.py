"""
Auditoria técnica de mudanças de política de booking (estrutura para API futura).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from sqlalchemy.orm import Session

from app.modules.booking.domain.policy.models import BookingPolicyAudit


def record_policy_change(
    db: Session,
    *,
    company_id: int,
    action: str,
    before: Optional[Mapping[str, Any]] = None,
    after: Optional[Mapping[str, Any]] = None,
    actor_user_id: Optional[int] = None,
    reason: Optional[str] = None,
    commit: bool = False,
) -> BookingPolicyAudit:
    """
    Persiste um evento de auditoria de política de booking.

    Preparado para consumo futuro por endpoints de configuração (FIX-CONFIG-02).
    Não cria HTTP; apenas grava a trilha técnica.

    Args:
        db: Sessão SQLAlchemy.
        company_id: Tenant afetado.
        action: Ação (ex.: ``create``, ``update``, ``deactivate``, ``resolve_fallback``).
        before: Snapshot anterior (opcional).
        after: Snapshot posterior (opcional).
        actor_user_id: Usuário ator (opcional).
        reason: Motivo textual (opcional).
        commit: Se True, faz commit imediato; caso contrário só ``flush``.

    Returns:
        Instância ``BookingPolicyAudit`` persistida (flushada).

    Raises:
        ValueError: Se ``company_id`` ou ``action`` forem inválidos.
    """
    if company_id is None or not isinstance(company_id, int) or company_id <= 0:
        raise ValueError("company_id deve ser int positivo")
    if not action or not isinstance(action, str):
        raise ValueError("action é obrigatória")

    row = BookingPolicyAudit(
        company_id=company_id,
        actor_user_id=actor_user_id,
        action=action.strip(),
        before_json=dict(before) if before is not None else None,
        after_json=dict(after) if after is not None else None,
        reason=reason,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row
