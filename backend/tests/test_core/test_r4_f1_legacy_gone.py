"""R4-F1 — HTTP 410 Gone em rotas legado de booking (RFC-003 M6)."""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.legacy_gone import match_booking_legacy_gone
from app.shared.events.event_catalog import event_catalog_entries


def test_app_version_r4_f1():
    """Versão da release R4-F1 (pin exato relaxado em R4-F2+; ver test_app_version_r4_f2)."""
    assert settings.APP_VERSION.startswith("2.")


def test_match_booking_legacy_gone_prefixes():
    """Mapa 410 cobre agenda/agendamentos e reservations."""
    assert match_booking_legacy_gone("/agenda/agendamentos").successor == "/v1/bookings"
    assert match_booking_legacy_gone("/agenda/agendamentos/9").successor == "/v1/bookings"
    assert match_booking_legacy_gone("/reservations").successor == "/v1/bookings"
    assert match_booking_legacy_gone("/reservations/1").successor == "/v1/bookings"
    assert match_booking_legacy_gone("/agenda/disponibilidade") is None
    assert match_booking_legacy_gone("/v1/bookings") is None


def test_get_agenda_agendamentos_gone(client: TestClient):
    """GET /agenda/agendamentos → 410 + Link successor."""
    response = client.get("/agenda/agendamentos")
    assert response.status_code == 410
    body = response.json()
    assert body["successor"] == "/v1/bookings"
    assert body["enforcement"] == "gone"
    assert response.headers.get("Deprecation") == "true"
    assert "/v1/bookings" in (response.headers.get("Link") or "")


def test_get_reservations_gone(client: TestClient):
    """GET /reservations → 410."""
    response = client.get("/reservations")
    assert response.status_code == 410
    assert response.json()["successor"] == "/v1/bookings"


def test_post_agenda_agendamentos_gone(client: TestClient):
    """POST legado também 410 (não mais 405/409)."""
    response = client.post("/agenda/agendamentos", json={})
    assert response.status_code == 410
    assert response.headers.get("X-CoreFlow-Enforcement") == "gone"


def test_disponibilidade_still_available(
    client: TestClient, tranca_exemplo, service_image_exemplo
):
    """/agenda/disponibilidade permanece (Sunset only)."""
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


def test_reservation_created_catalog_status_gone():
    """ADR-027 — reservation.created marcado gone no catálogo."""
    entry = next(
        e for e in event_catalog_entries() if e["event_type"] == "reservation.created"
    )
    assert entry["status"] == "gone"
