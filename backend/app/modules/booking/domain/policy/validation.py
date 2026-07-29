"""
Validação e merge profundo de documentos de política de booking.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Tuple

from pydantic import ValidationError

from app.modules.booking.domain.policy.defaults import defaults_as_dict
from app.modules.booking.domain.policy.schemas import BookingPolicy


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Faz merge profundo de dicts (override vence em folhas).

    Listas e escalares do override substituem integralmente o valor base.
    Dicts aninhados são mesclados recursivamente.

    Args:
        base: Documento base (defaults).
        override: Patch parcial ou completo.

    Returns:
        Novo dict mesclado (não muta os argumentos).
    """
    result: Dict[str, Any] = deepcopy(dict(base))
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def parse_booking_policy(document: Mapping[str, Any]) -> BookingPolicy:
    """
    Valida e materializa um documento completo como ``BookingPolicy``.

    Args:
        document: Dict já mesclado (defaults + override).

    Returns:
        Política imutável validada.

    Raises:
        ValidationError: Documento inválido.
    """
    return BookingPolicy.model_validate(dict(document))


def merge_and_validate(
    override: Mapping[str, Any] | None,
) -> Tuple[BookingPolicy | None, str | None]:
    """
    Aplica override sobre defaults e valida o resultado.

    Args:
        override: Patch parcial/completo ou None/vazio.

    Returns:
        Tupla ``(policy, error_message)``. Em sucesso ``error_message`` é None;
        em falha ``policy`` é None e a mensagem descreve o erro.
    """
    base = defaults_as_dict()
    if not override:
        return parse_booking_policy(base), None
    try:
        merged = deep_merge(base, override)
        return parse_booking_policy(merged), None
    except ValidationError as exc:
        return None, str(exc)
    except (TypeError, ValueError) as exc:
        return None, str(exc)
