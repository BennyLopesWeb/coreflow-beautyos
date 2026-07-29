"""
Defaults de instalação e fallback seguro (FIX-CONFIG-01).
"""
from __future__ import annotations

from copy import deepcopy

from app.modules.booking.domain.policy.schemas import (
    BookingPolicy,
    CancellationPolicy,
    ExpirationPolicy,
    ManualStatusPolicy,
    ReversalPolicy,
    default_manual_transitions,
)


def get_installation_defaults() -> BookingPolicy:
    """
    Retorna a política padrão de instalação (imutável).

    Espelha os comportamentos atuais hardcoded (expire 2h, cancel 24h)
    com reversões desabilitadas e proteção financeira ativa.

    Returns:
        ``BookingPolicy`` congelada com defaults seguros.
    """
    return BookingPolicy(
        expiration=ExpirationPolicy(
            enabled=True,
            after_hours=2,
            reference="created_at",
            eligible_statuses=("pending_payment",),
            require_unpaid_deposit=True,
            result_status="expired",
            touch_payment_status=False,
        ),
        cancellation=CancellationPolicy(
            enabled=True,
            allowed_roles=("owner", "admin"),
            client_allowed=False,
            approved_min_hours_before=24,
            allowed_from_statuses=("pending", "approved"),
            set_payment_cancelled=True,
            soft_delete=True,
        ),
        reversal_cancelled=ReversalPolicy(
            enabled=False,
            allowed_roles=(),
            mode="new_booking_only",
        ),
        reversal_expired=ReversalPolicy(
            enabled=False,
            allowed_roles=(),
            mode="new_booking_only",
        ),
        manual_status=ManualStatusPolicy(
            enabled=True,
            allowed_transitions=default_manual_transitions(),
            block_financial_reopen=True,
        ),
    )


def get_safe_fallback_policy() -> BookingPolicy:
    """
    Fallback fail-closed usado quando override inválido ou erro de leitura.

    Returns:
        Cópia dos defaults de instalação (nunca política permissiva inventada).
    """
    return get_installation_defaults()


def defaults_as_dict() -> dict:
    """
    Defaults como dict mutável para merges profundos.

    Returns:
        Dict JSON dos defaults de instalação.
    """
    return deepcopy(get_installation_defaults().to_public_dict())
