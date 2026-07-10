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
def test_criar_agendamento(client, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa POST /agenda/agendamentos"""
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)
    
    data = {
        "cliente_id": cliente_exemplo.id,
        "tranca_id": tranca_exemplo.id,
        "service_image_id": service_image_exemplo.id,
        "data_hora": data_hora.isoformat(),
        "observacoes": "Teste"
    }
    
    response = client.post("/agenda/agendamentos", json=data)
    
    assert response.status_code == 201
    assert response.json()["cliente_id"] == cliente_exemplo.id
    assert response.json()["service_image_id"] == service_image_exemplo.id
    assert response.json()["sinal_pago"] is False


@pytest.mark.integration
def test_confirmar_pagamento_sinal(client, cliente_exemplo, tranca_exemplo, service_image_exemplo, db):
    """Testa POST /pagamentos/sinal"""
    # Cria agendamento
    from app.services.agendamento_service import AgendamentoService
    from app.schemas.agendamento import AgendamentoCreate
    from datetime import datetime, timedelta
    
    service = AgendamentoService(db)
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)
    
    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora
    )
    agendamento = service.criar_agendamento(agendamento_data)
    
    # Confirma pagamento
    data = {
        "agendamento_id": agendamento.id,
        "valor": 45.0,
    }
    
    response = client.post("/pagamentos/sinal", json=data)
    
    assert response.status_code == 200
    assert response.json()["sinal_pago"] is True

