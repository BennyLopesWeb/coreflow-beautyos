"""
Validação e merge profundo de documentos de política de booking.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Tuple

from pydantic import ValidationError

from app.modules.booking.domain.policy.defaults import defaults_as_dict
from app.modules.booking.domain.policy.schemas import ActivationPolicy, BookingPolicy


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Faz merge profundo de dicts (override vence em folhas).

    Listas e escalares do override substituem integralmente o valor base.
    Dicts aninhados são mesclados recursivamente.

    Exceção (CONFIG-DEPOSIT-POLICY-01): o grupo ``activation`` é substituído
    por completo quando o override informa um ``mode`` diferente do base,
    para não misturar campos mutuamente exclusivos entre modos.

    Args:
        base: Documento base (defaults).
        override: Patch parcial ou completo.

    Returns:
        Novo dict mesclado (não muta os argumentos).
    """
    result: Dict[str, Any] = deepcopy(dict(base))
    for key, value in override.items():
        if (
            key == "activation"
            and key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            base_mode = result[key].get("mode")
            new_mode = value.get("mode")
            if new_mode is not None and new_mode != base_mode:
                result[key] = deepcopy(value)
                continue
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
        # Validar o grupo ``activation`` do override em isolamento: não completar
        # campos obrigatórios do modo a partir dos defaults da plataforma.
        activation_override = override.get("activation")
        if isinstance(activation_override, dict):
            ActivationPolicy.model_validate(activation_override)
        merged = deep_merge(base, override)
        return parse_booking_policy(merged), None
    except ValidationError as exc:
        return None, str(exc)
    except (TypeError, ValueError) as exc:
        return None, str(exc)
