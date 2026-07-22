"""
Testes de integração - Endpoints de Agendamentos
"""
import pytest
from datetime import datetime, timedelta


@pytest.mark.integration
def test_consultar_disponibilidade(client, tranca_exemplo, service_image_exemplo):
    """Testa GET /agenda/disponibilidade com modelo selecionado"""
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    response = client.get(
        "/agenda/disponibilidade",
        params={
            "data": data_hora.isoformat(),
            "tranca_id": tranca_exemplo.id,
            "service_image_id": service_image_exemplo.id,
        },
    )

    assert response.status_code == 200
    assert "horarios" in response.json()
    assert isinstance(response.json()["horarios"], list)


@pytest.mark.integration
def test_criar_agendamento_legado_removido(client, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """R3-F3 — POST /agenda/agendamentos removido (use /v1/bookings)."""
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    data = {
        "cliente_id": cliente_exemplo.id,
        "tranca_id": tranca_exemplo.id,
        "service_image_id": service_image_exemplo.id,
        "data_hora": data_hora.isoformat(),
        "observacoes": "Teste",
    }

    response = client.post("/agenda/agendamentos", json=data)
    assert response.status_code in (405, 410)


@pytest.mark.integration
def test_confirmar_pagamento_sinal_agendamento_legado_sempre_falha(client):
    """
    POST /pagamentos/sinal responde 410 Gone (R4-F9 — LegacyGoneMiddleware).

    A tabela ``agendamentos`` foi removida (R4-F8); o path legado de
    pagamento foi sunsetado. Use
    ``POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal``.
    """
    data = {
        "agendamento_id": 999999,
        "valor": 45.0,
    }

    response = client.post("/pagamentos/sinal", json=data)

    assert response.status_code == 410

