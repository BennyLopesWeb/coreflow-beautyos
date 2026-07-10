"""Testes middleware Sunset — rotas legado."""
from datetime import datetime, timedelta

from app.core.legacy_sunset import match_legacy_sunset


def test_sunset_headers_on_trancas(client):
    """GET /trancas inclui headers RFC 8594 de depreciação."""
    response = client.get("/trancas")
    assert response.status_code == 200
    assert "Sunset" in response.headers
    assert response.headers.get("Deprecation") == "true"
    assert "/v1/catalogs" in response.headers.get("Link", "")


def test_sunset_headers_on_agenda_disponibilidade(
    client, tranca_exemplo, service_image_exemplo
):
    """GET /agenda/disponibilidade aponta sucessor v1 scheduling."""
    target = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    response = client.get(
        "/agenda/disponibilidade",
        params={
            "data": f"{target}T08:00:00",
            "tranca_id": tranca_exemplo.id,
            "service_image_id": service_image_exemplo.id,
        },
    )
    assert response.status_code == 200
    assert "Sunset" in response.headers
    assert "/v1/scheduling/availability" in response.headers.get("Link", "")


def test_no_sunset_on_v1_catalogs(client):
    """Rotas v1 não recebem headers Sunset."""
    response = client.get("/v1/catalogs")
    assert response.status_code == 200
    assert "Sunset" not in response.headers


def test_match_legacy_sunset_specific_path():
    """Rotas específicas têm prioridade sobre prefixos genéricos."""
    rule = match_legacy_sunset("/agenda/disponibilidade")
    assert rule is not None
    assert rule.successor == "/v1/scheduling/availability"

    rule_agenda = match_legacy_sunset("/agenda/agendamentos/1")
    assert rule_agenda is not None
    assert rule_agenda.successor == "/v1/bookings"
