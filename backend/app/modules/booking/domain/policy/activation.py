"""
Política de ativação financeira da reserva (FIX-BOOKING-MIN-DEPOSIT-QUOTE-01).

Fórmula compartilhada com o expirador (FIX-EXPIRATION-02C):

    minimum_activation_cents = min(ceil(total_service_cents * 20 / 100), 10000)
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

NumberLike = Union[Decimal, int, float, str]

# Teto: R$ 100,00
ACTIVATION_CAP_CENTS = 10_000
# Percentual sobre o total do serviço
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


def calculate_minimum_activation_cents(total_service_cents: int) -> int:
    """
    Calcula o mínimo de entrada para ativar a reserva (centavos, aritmética inteira).

    Fórmula::

        min((total_service_cents * 20 + 99) // 100, 10000)

    Args:
        total_service_cents: Total do serviço em centavos (deve ser > 0).

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
    twenty_pct = (total_service_cents * ACTIVATION_PERCENT + 99) // 100
    return min(twenty_pct, ACTIVATION_CAP_CENTS)


def meets_minimum_activation(
    *,
    total_service_cents: int,
    paid_cents: int,
) -> bool:
    """
    Indica se o valor pago atinge o mínimo de ativação (inclusive).

    Args:
        total_service_cents: Total do serviço em centavos (> 0).
        paid_cents: Valor efetivamente pago em centavos (>= 0).

    Returns:
        ``True`` se ``paid_cents >= minimum``.

    Raises:
        ValueError: Se totais forem inválidos.
    """
    if not isinstance(paid_cents, int) or isinstance(paid_cents, bool):
        raise ValueError("paid_cents deve ser int")
    if paid_cents < 0:
        raise ValueError("paid_cents não pode ser negativo")
    minimum = calculate_minimum_activation_cents(total_service_cents)
    return paid_cents >= minimum


def minimum_activation_from_price_total(
    price_total: Optional[NumberLike],
) -> Optional[int]:
    """
    Calcula o mínimo a partir de ``price_total`` em reais.

    Args:
        price_total: Preço total do serviço/booking.

    Returns:
        Mínimo em centavos, ou ``None`` se o total for ausente/inválido/zero.
    """
    total_cents = money_to_cents(price_total)
    if total_cents is None or total_cents <= 0:
        return None
    return calculate_minimum_activation_cents(total_cents)
