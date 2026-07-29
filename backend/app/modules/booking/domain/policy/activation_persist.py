"""
Persistência do snapshot de ativação no CoreBooking (CONFIG-DEPOSIT-POLICY-01).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.activation import (
    build_activation_policy_snapshot,
    calculate_minimum_activation_cents,
    money_to_cents,
)
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.policy.resolver import BookingPolicyResolver

logger = logging.getLogger("trancapro.activation_policy")


def persist_activation_snapshot_on_booking(
    db: Session,
    *,
    booking_id: int,
    company_id: int,
    price_total: Any = None,
) -> Optional[int]:
    """
    Calcula e grava ``minimum_activation_cents`` + snapshot no booking.

    Deve rodar na mesma transação da criação. Em falha de política inválida
    na leitura, usa fallback legado (resolver já faz fail-closed).

    Args:
        db: Sessão SQLAlchemy.
        booking_id: ID ``core_bookings``.
        company_id: Tenant.
        price_total: Preço opcional; se omitido, lê do booking.

    Returns:
        Mínimo persistido em centavos, ou ``None`` se booking ausente.
    """
    row = (
        db.query(CoreBooking)
        .filter(
            CoreBooking.id == int(booking_id),
            CoreBooking.company_id == int(company_id),
        )
        .first()
    )
    if row is None:
        return None

    total_src = price_total if price_total is not None else row.price_total
    total_cents = money_to_cents(total_src)
    if total_cents is None or total_cents <= 0:
        logger.warning(
            "Ativação: booking_id=%s company_id=%s sem price_total válido "
            "— snapshot não gravado",
            booking_id,
            company_id,
        )
        return None

    try:
        policy = BookingPolicyResolver(db).resolve(int(company_id))
        activation = policy.activation
    except Exception:
        logger.exception(
            "Falha ao resolver ActivationPolicy company_id=%s — fallback legado",
            company_id,
        )
        activation = None

    minimum = calculate_minimum_activation_cents(
        total_cents, activation=activation
    )
    cfg = (
        db.query(BookingPolicyConfig)
        .filter(
            BookingPolicyConfig.company_id == int(company_id),
            BookingPolicyConfig.is_active.is_(True),
        )
        .first()
    )
    policy_version = int(cfg.version) if cfg is not None else 0

    from app.modules.booking.domain.policy.schemas import default_activation_policy

    act = activation if activation is not None else default_activation_policy()
    snap = build_activation_policy_snapshot(
        policy_version=policy_version,
        activation=act,
        price_total_cents=total_cents,
        minimum_activation_cents=minimum,
    )
    row.minimum_activation_cents = minimum
    row.activation_policy_snapshot = snap
    db.flush()
    return minimum
