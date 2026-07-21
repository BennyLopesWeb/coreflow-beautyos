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
def test_confirmar_pagamento_sinal(client, cliente_exemplo, tranca_exemplo, service_image_exemplo, db):
    """Testa POST /pagamentos/sinal sobre reserva legado (R4-F4: criada via ORM direto)."""
    from decimal import Decimal
    from datetime import datetime, timedelta

    from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
    from app.utils.service_image_precos import resolver_precos_imagem

    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    agendamento = Agendamento(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora,
        status=ReservationStatus.PENDING_PAYMENT,
        sinal_pago=False,
        valor_total=precos["valor_total"],
        percentual_sinal=service_image_exemplo.percentual_sinal or Decimal("0.30"),
        valor_sinal=precos["valor_sinal"],
        valor_restante=precos["valor_restante"],
        status_pagamento=StatusPagamento.PENDING_PAYMENT,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)

    # Confirma pagamento
    data = {
        "agendamento_id": agendamento.id,
        "valor": 45.0,
    }
    
    response = client.post("/pagamentos/sinal", json=data)
    
    assert response.status_code == 200
    assert response.json()["sinal_pago"] is True

