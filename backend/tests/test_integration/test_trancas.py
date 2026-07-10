"""
Testes de integração - Endpoints de Tranças
"""
import pytest
from decimal import Decimal


@pytest.mark.integration
def test_listar_trancas(client):
    """Testa GET /trancas"""
    response = client.get("/trancas")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.integration
def test_criar_tranca(client, admin_headers):
    """Testa POST /trancas (categoria sem preço/duração)"""
    data = {
        "nome": "Trança Teste",
        "descricao": "Descrição teste",
        "imagens": [],
        "ativo": True,
    }

    response = client.post("/trancas", json=data, headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Trança Teste"
    assert body["descricao"] == "Descrição teste"
    assert "duracao_minutos" not in body
    assert "valor_total" not in body


@pytest.mark.integration
def test_criar_tranca_sem_admin_retorna_403(client):
    """POST /trancas exige administrador autenticado"""
    data = {
        "nome": "Trança Teste",
        "imagens": [],
        "ativo": True,
    }

    response = client.post("/trancas", json=data)

    assert response.status_code in (401, 403)


@pytest.mark.integration
def test_obter_tranca(client, tranca_exemplo):
    """Testa GET /trancas/{id}"""
    response = client.get(f"/trancas/{tranca_exemplo.id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == tranca_exemplo.id
    assert response.json()["nome"] == "Box Braids"

