"""
Avaliação pura da janela de cancelamento de bookings approved (FIX-CANCEL-POLICY-01).

Reutilizável pelo cancelamento oficial e, futuramente, pelo PATCH admin
(FIX-CANCEL-POLICY-02). Sem acesso a banco ou sessão SQLAlchemy.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.booking.domain.value_objects.booking_types import BookingLifecycleStatus


def ensure_utc(value: datetime) -> datetime:
    """
    Normaliza datetime para UTC, preservando a semântica atual do adapter.

    Args:
        value: Datetime de entrada (naive ou aware).

    Returns:
        Datetime aware em UTC. Naive é interpretado como UTC (compatível
        com ``LegacyCancelPolicyAdapter`` pré-FIX-CANCEL-POLICY-01).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def can_cancel_approved(
    now_utc: datetime,
    starts_at_utc: datetime,
    approved_min_hours_before: int,
) -> bool:
    """
    Avalia se um booking ``approved`` pode ser cancelado pela janela.

    Regra (limite inclusivo):

    ``now_utc <= starts_at_utc - timedelta(hours=approved_min_hours_before)``

    Args:
        now_utc: Relógio atual (será normalizado para UTC).
        starts_at_utc: Início do slot (naive = UTC; aware convertido).
        approved_min_hours_before: Horas mínimas de antecedência (N ≥ 0).

    Returns:
        True se o cancelamento está dentro da janela permitida.

    Raises:
        ValueError: Se ``approved_min_hours_before`` for negativo ou não-int.
    """
    if not isinstance(approved_min_hours_before, int) or isinstance(
        approved_min_hours_before, bool
    ):
        raise ValueError("approved_min_hours_before deve ser int")
    if approved_min_hours_before < 0:
        raise ValueError("approved_min_hours_before não pode ser negativo")

    now = ensure_utc(now_utc)
    starts = ensure_utc(starts_at_utc)
    deadline = starts - timedelta(hours=approved_min_hours_before)
    return now <= deadline


def may_cancel_for_lifecycle(
    status: BookingLifecycleStatus,
    now_utc: datetime,
    starts_at: datetime,
    approved_min_hours_before: int,
) -> bool:
    """
    Avalia cancelamento por lifecycle (pending ignora janela; approved aplica).

    Preparado para consumo pelo ``CancelPolicyPort`` e pelo PATCH futuro.
    Estados fora de pending/approved retornam False (a FSM do domínio
    continua sendo a fonte de verdade da transição).

    Args:
        status: Lifecycle canônico do booking.
        now_utc: Relógio atual.
        starts_at: Início vigente do slot.
        approved_min_hours_before: N da política do tenant.

    Returns:
        True se a política de janela permite cancelar neste status.
    """
    if status == BookingLifecycleStatus.PENDING:
        return True
    if status != BookingLifecycleStatus.APPROVED:
        return False
    return can_cancel_approved(now_utc, starts_at, approved_min_hours_before)
