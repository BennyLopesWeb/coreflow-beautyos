"""
Helpers para preços e duração de modelos de trança.
Toda informação comercial pertence ao modelo — nunca à categoria.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict

PERCENTUAL_SINAL_PADRAO = Decimal("0.30")


def calcular_sinal(
    valor_total: Decimal,
    percentual: Decimal = PERCENTUAL_SINAL_PADRAO,
) -> Decimal:
    """
    Calcula o sinal a partir do valor total e percentual do modelo.

    Args:
        valor_total: Valor total do serviço.
        percentual: Percentual de sinal (ex: 0.30 = 30%).

    Returns:
        Valor do sinal arredondado em 2 casas decimais.
    """
    return (valor_total * percentual).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_saldo_restante(valor_total: Decimal, valor_sinal: Decimal) -> Decimal:
    """
    Calcula o saldo restante após o sinal.

    Args:
        valor_total: Valor total do modelo.
        valor_sinal: Valor do sinal.

    Returns:
        Saldo restante arredondado.
    """
    return (valor_total - valor_sinal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percentual_modelo(img: Any) -> Decimal:
    """
    Obtém percentual de sinal do modelo ou padrão 30%.

    Args:
        img: Instância ServiceImage.

    Returns:
        Percentual como Decimal.
    """
    if img.percentual_sinal is not None:
        return Decimal(str(img.percentual_sinal))
    return PERCENTUAL_SINAL_PADRAO


def resolver_precos_imagem(img: Any, tranca: Any = None) -> Dict[str, Any]:
    """
    Resolve valores comerciais exclusivamente do modelo.

    Args:
        img: Instância ServiceImage (modelo).
        tranca: Ignorado — mantido por compatibilidade de assinatura.

    Returns:
        Dict com valor_total, valor_sinal, valor_restante, duracao_minutos, percentual_sinal.

    Raises:
        ValueError: Se modelo sem preço ou duração cadastrados.
    """
    if img.valor_total is None or Decimal(str(img.valor_total)) <= 0:
        raise ValueError("Modelo sem preço cadastrado")

    if img.duracao_minutos is None or int(img.duracao_minutos) <= 0:
        raise ValueError("Modelo sem duração estimada cadastrada")

    valor_total = Decimal(str(img.valor_total))
    percentual = _percentual_modelo(img)
    valor_sinal = calcular_sinal(valor_total, percentual)
    valor_restante = calcular_saldo_restante(valor_total, valor_sinal)

    return {
        "valor_total": valor_total,
        "valor_sinal": valor_sinal,
        "valor_restante": valor_restante,
        "duracao_minutos": int(img.duracao_minutos),
        "percentual_sinal": percentual,
    }


def validar_precos(valor_total: Decimal, valor_sinal: Decimal | None = None) -> None:
    """
    Valida preço do modelo.

    Args:
        valor_total: Valor total do modelo.
        valor_sinal: Ignorado.

    Raises:
        ValueError: Se valor total for inválido.
    """
    if valor_total <= 0:
        raise ValueError("Preço do modelo deve ser maior que zero")
