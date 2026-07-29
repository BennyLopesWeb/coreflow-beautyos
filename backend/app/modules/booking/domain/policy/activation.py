"""
Política de ativação financeira da reserva.

CONFIG-DEPOSIT-POLICY-01: cálculo configurável por tenant via
``ActivationPolicy``. Fallback legado (ausente/inválido na leitura):

    minimum_activation_cents = min(ceil(total * 20 / 100), 10000)
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Mapping, Optional, Union

from app.modules.booking.domain.policy.schemas import (
    ActivationPolicy,
    default_activation_policy,
)

NumberLike = Union[Decimal, int, float, str]

# Constantes legadas (fallback e default de instalação)
ACTIVATION_CAP_CENTS = 10_000
ACTIVATION_PERCENT = 20


def money_to_cents(value: Optional[NumberLike]) -> Optional[int]:
    """
    Converte valor monetário em reais para centavos inteiros.

    Args:
        value: Valor em reais (``Decimal``, int, float ou str), ou ``None``.

    Returns:
        Centavos >= 0, ou ``None`` se ausente/inválido/negativo.
    """
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except Exception:
        return None
    if amount < 0:
        return None
    cents = (amount * Decimal("100")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(cents)


def cents_to_decimal(cents: int) -> Decimal:
    """
    Converte centavos inteiros para ``Decimal`` em reais (2 casas).

    Args:
        cents: Valor em centavos (>= 0).

    Returns:
        Valor em reais com duas casas decimais.

    Raises:
        ValueError: Se ``cents`` for negativo.
    """
    if cents < 0:
        raise ValueError("cents não pode ser negativo")
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def _ceil_percent(total_service_cents: int, percentage: int) -> int:
    """
    Aplica percentual com arredondamento para cima (aritmética inteira).

    Args:
        total_service_cents: Total em centavos (> 0).
        percentage: Percentual inteiro 0–100.

    Returns:
        Valor bruto em centavos.
    """
    return (total_service_cents * int(percentage) + 99) // 100


def calculate_minimum_activation_cents(
    total_service_cents: int,
    *,
    activation: Optional[ActivationPolicy] = None,
) -> int:
    """
    Calcula o mínimo de entrada para ativar a reserva (centavos).

    Sem ``activation`` (ou equivalente ao default), preserva a fórmula legada
    ``min(ceil(total*20%), 10000)``.

    Args:
        total_service_cents: Total do serviço em centavos (deve ser > 0).
        activation: Política tipada do tenant; ``None`` = fallback legado.

    Returns:
        Mínimo de ativação em centavos.

    Raises:
        ValueError: Se ``total_service_cents`` não for int positivo.
    """
    if not isinstance(total_service_cents, int) or isinstance(
        total_service_cents, bool
    ):
        raise ValueError("total_service_cents deve ser int")
    if total_service_cents <= 0:
        raise ValueError("total_service_cents deve ser positivo")

    policy = activation if activation is not None else default_activation_policy()

    if policy.mode == "percentage_with_cap":
        raw = _ceil_percent(total_service_cents, int(policy.percentage or 0))
        return min(raw, int(policy.cap_cents or 0))

    if policy.mode == "tiered_percentage":
        threshold = int(policy.high_value_threshold_cents or 0)
        if total_service_cents < threshold:
            applied = int(policy.standard_percentage or 0)
        else:
            applied = int(policy.high_value_percentage or 0)
        minimum = _ceil_percent(total_service_cents, applied)
        if policy.cap_cents is not None:
            minimum = min(minimum, int(policy.cap_cents))
        return minimum

    # Modo desconhecido na leitura → fallback legado (não usar valores inválidos)
    raw = _ceil_percent(total_service_cents, ACTIVATION_PERCENT)
    return min(raw, ACTIVATION_CAP_CENTS)


def applied_percentage_for(
    total_service_cents: int,
    activation: ActivationPolicy,
) -> int:
    """
    Percentual efetivamente aplicado ao total para o snapshot.

    Args:
        total_service_cents: Total em centavos.
        activation: Política tipada.

    Returns:
        Percentual inteiro aplicado.
    """
    if activation.mode == "percentage_with_cap":
        return int(activation.percentage or 0)
    threshold = int(activation.high_value_threshold_cents or 0)
    if total_service_cents < threshold:
        return int(activation.standard_percentage or 0)
    return int(activation.high_value_percentage or 0)


def build_activation_policy_snapshot(
    *,
    policy_version: int,
    activation: ActivationPolicy,
    price_total_cents: int,
    minimum_activation_cents: int,
    calculated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Monta o JSON de snapshot imutável gravado no booking.

    Args:
        policy_version: Versão do override ativo (0 se só defaults).
        activation: Política aplicada.
        price_total_cents: Total usado no cálculo.
        minimum_activation_cents: Mínimo calculado.
        calculated_at: Momento do cálculo (UTC).

    Returns:
        Dict serializável para ``activation_policy_snapshot``.
    """
    when = calculated_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    applied = applied_percentage_for(price_total_cents, activation)
    snap: Dict[str, Any] = {
        "policy_version": int(policy_version),
        "mode": activation.mode,
        "currency": activation.currency,
        "price_total_cents": int(price_total_cents),
        "applied_percentage": int(applied),
        "cap_cents": activation.cap_cents,
        "minimum_activation_cents": int(minimum_activation_cents),
        "calculated_at": when.isoformat(),
    }
    if activation.mode == "percentage_with_cap":
        snap["percentage"] = activation.percentage
    else:
        snap["standard_percentage"] = activation.standard_percentage
        snap["high_value_threshold_cents"] = activation.high_value_threshold_cents
        snap["high_value_percentage"] = activation.high_value_percentage
    return snap


def snapshot_is_coherent(
    snapshot: Optional[Mapping[str, Any]],
    minimum_activation_cents: Optional[int],
) -> bool:
    """
    Indica se o snapshot persistido é utilizável.

    Args:
        snapshot: JSON do booking.
        minimum_activation_cents: Coluna paralela.

    Returns:
        ``True`` se coerente e seguro para decisões automáticas.
    """
    if snapshot is None or minimum_activation_cents is None:
        return False
    try:
        snap_min = int(snapshot.get("minimum_activation_cents"))
        mode = snapshot.get("mode")
        if mode not in ("percentage_with_cap", "tiered_percentage"):
            return False
        if snap_min != int(minimum_activation_cents):
            return False
        if snap_min < 0:
            return False
        return True
    except Exception:
        return False


def resolve_booking_minimum_activation_cents(booking: Any) -> int:
    """
    Resolve o mínimo para confirmação/expiração a partir do booking.

    - Snapshot coerente → usa ``minimum_activation_cents`` persistido.
    - Snapshot inválido → fórmula legada (nunca a config atual do tenant).
    - Booking legado (sem snapshot) → fórmula legada.

    Args:
        booking: ORM ``CoreBooking`` (ou duck-type com price_total/campos).

    Returns:
        Mínimo em centavos.

    Raises:
        ValueError: Preço total inválido quando precisa calcular legado.
    """
    stored = getattr(booking, "minimum_activation_cents", None)
    snap = getattr(booking, "activation_policy_snapshot", None)
    if snapshot_is_coherent(snap, stored):
        return int(stored)

    total_cents = money_to_cents(getattr(booking, "price_total", None))
    if total_cents is None or total_cents <= 0:
        raise ValueError("price_total inválido para mínimo de ativação")
    # Legado explícito — sem ActivationPolicy do tenant atual
    return calculate_minimum_activation_cents(total_cents, activation=None)


def meets_minimum_activation(
    *,
    total_service_cents: int,
    paid_cents: int,
    activation: Optional[ActivationPolicy] = None,
) -> bool:
    """
    Indica se o valor pago atinge o mínimo de ativação (inclusive).

    Args:
        total_service_cents: Total do serviço em centavos (> 0).
        paid_cents: Valor efetivamente pago em centavos (>= 0).
        activation: Política opcional.

    Returns:
        ``True`` se ``paid_cents >= minimum``.

    Raises:
        ValueError: Se totais forem inválidos.
    """
    if not isinstance(paid_cents, int) or isinstance(paid_cents, bool):
        raise ValueError("paid_cents deve ser int")
    if paid_cents < 0:
        raise ValueError("paid_cents não pode ser negativo")
    minimum = calculate_minimum_activation_cents(
        total_service_cents, activation=activation
    )
    return paid_cents >= minimum


def minimum_activation_from_price_total(
    price_total: Optional[NumberLike],
    *,
    activation: Optional[ActivationPolicy] = None,
) -> Optional[int]:
    """
    Calcula o mínimo a partir de ``price_total`` em reais.

    Args:
        price_total: Preço total do serviço/booking.
        activation: Política opcional do tenant.

    Returns:
        Mínimo em centavos, ou ``None`` se o total for ausente/inválido/zero.
    """
    total_cents = money_to_cents(price_total)
    if total_cents is None or total_cents <= 0:
        return None
    return calculate_minimum_activation_cents(
        total_cents, activation=activation
    )
