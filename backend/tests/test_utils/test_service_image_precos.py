"""
Testes do cálculo de preços por modelo.
"""
import pytest
from decimal import Decimal

from app.utils.service_image_precos import (
    calcular_sinal,
    calcular_saldo_restante,
    resolver_precos_imagem,
    PERCENTUAL_SINAL_PADRAO,
)


@pytest.mark.unit
def test_calcular_sinal_30_porcento():
    """Sinal deve ser 30% do valor total, arredondado."""
    assert calcular_sinal(Decimal("180.00")) == Decimal("54.00")
    assert calcular_sinal(Decimal("250.00")) == Decimal("75.00")
    assert calcular_sinal(Decimal("450.00")) == Decimal("135.00")


@pytest.mark.unit
def test_calcular_saldo_restante():
    """Saldo restante = total - sinal."""
    assert calcular_saldo_restante(Decimal("450.00"), Decimal("135.00")) == Decimal("315.00")
    assert calcular_saldo_restante(Decimal("180.00"), Decimal("54.00")) == Decimal("126.00")


@pytest.mark.unit
def test_resolver_precos_imagem_com_foto(db, tranca_exemplo, service_image_exemplo):
    """Preços efetivos vêm exclusivamente do modelo."""
    precos = resolver_precos_imagem(service_image_exemplo)
    assert precos["valor_total"] == Decimal("150.00")
    assert precos["valor_sinal"] == Decimal("45.00")
    assert precos["valor_restante"] == Decimal("105.00")
    assert precos["percentual_sinal"] == PERCENTUAL_SINAL_PADRAO


@pytest.mark.unit
def test_resolver_precos_sem_preco_falha(db, tranca_exemplo, service_image_exemplo):
    """Modelo sem preço não pode ser usado em reserva."""
    service_image_exemplo.valor_total = None
    service_image_exemplo.duracao_minutos = None
    with pytest.raises(ValueError, match="sem preço"):
        resolver_precos_imagem(service_image_exemplo)
