"""Testes R1-F1 — Platform governance: flags, route map, event catalog, telemetria."""
import pytest

from app.core.feature_flags import FeatureFlagService, feature_flags
from app.core.legacy_route_map import classify_api_layer, find_core_successor, route_mapping_document
from app.core.prometheus_metrics import record_http_request, metrics_summary
from app.shared.events.event_catalog import event_catalog_entries, event_catalog_summary
from app.shared.acl.booking_port import LegacyBookingAdapter


def test_feature_flags_defaults():
    """Flags de migração com defaults seguros (R3-F2: booking core-only default True)."""
    flags = feature_flags.all_flags()
    assert flags["booking.core.enabled"]["enabled"] is True
    assert flags["resource.engine.enabled"]["enabled"] is False
    assert flags["ai.core.enabled"]["enabled"] is False
    assert flags["workflow.enabled"]["enabled"] is False
    assert flags["plugin.engine.enabled"]["enabled"] is False
    assert flags["legacy.telemetry.enabled"]["enabled"] is False


def test_feature_flags_unknown_raises():
    """Flag desconhecida levanta KeyError."""
    svc = FeatureFlagService()
    with pytest.raises(KeyError):
        svc.is_enabled("unknown.flag")


def test_classify_api_layer():
    """Classificação de camadas API."""
    assert classify_api_layer("/v1/bookings") == "core"
    assert classify_api_layer("/v1/platform/feature-flags") == "platform"
    assert classify_api_layer("/auth/login") == "identity"
    assert classify_api_layer("/reservations/1") == "beautyos"
    assert classify_api_layer("/agenda/agendamentos") == "legacy"
    assert classify_api_layer("/health") == "other"


def test_legacy_route_map_document():
    """Mapa legado→core contém escritas e leituras."""
    doc = route_mapping_document()
    assert doc["write_mappings"] >= 10
    assert doc["read_mappings"] >= 5
    layers = {m["layer"] for m in doc["mappings"]}
    assert "legacy" in layers
    assert "core" in layers or "beautyos" in layers


def test_find_core_successor():
    """Successor v1 para rota legado conhecida."""
    assert find_core_successor("POST", "/agendamentos") == "/v1/bookings"
    assert find_core_successor("GET", "/trancas") == "/v1/catalogs"


def test_event_catalog_complete():
    """Catálogo com eventos implementados e planejados."""
    summary = event_catalog_summary()
    assert summary["total"] >= 20
    assert summary["by_status"]["implemented"] >= 6
    types = {e["event_type"] for e in event_catalog_entries()}
    assert "booking.created" in types
    assert "customer.created" in types
    assert "notification.sent" in types


def test_event_catalog_api(client):
    """GET /v1/platform/event-catalog."""
    response = client.get("/v1/platform/event-catalog")
    assert response.status_code == 200
    assert response.json()["total"] >= 20


def test_feature_flags_api(client):
    """GET /v1/platform/feature-flags."""
    response = client.get("/v1/platform/feature-flags")
    assert response.status_code == 200
    assert "booking.core.enabled" in response.json()["flags"]


def test_legacy_route_map_api(client):
    """GET /v1/platform/legacy-route-map."""
    response = client.get("/v1/platform/legacy-route-map")
    assert response.status_code == 200
    assert len(response.json()["mappings"]) >= 15


def test_legacy_telemetry_headers(client, monkeypatch):
    """Middleware adiciona X-CoreFlow-Layer quando flag ativa."""
    monkeypatch.setattr(
        "app.core.feature_flags.settings.FEATURE_LEGACY_TELEMETRY_ENABLED",
        True,
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-CoreFlow-Layer") == "other"


def test_legacy_telemetry_successor_header(client, monkeypatch):
    """Rota legado expõe successor v1 com telemetria ativa."""
    monkeypatch.setattr(
        "app.core.feature_flags.settings.FEATURE_LEGACY_TELEMETRY_ENABLED",
        True,
    )
    response = client.get("/v1/catalogs")
    assert response.headers.get("X-CoreFlow-Layer") == "core"


def test_record_http_request_metrics():
    """record_http_request não falha com prometheus habilitado."""
    record_http_request("legacy", "GET", "2xx", 0.05)
    summary = metrics_summary()
    assert summary["enabled"] is True


def test_acl_booking_adapter_requires_db(db):
    """ACL adapter exige sessão DB (R1-F2 wiring)."""
    adapter = LegacyBookingAdapter(db)
    assert adapter._db is db
