"""Testes R1-F2 — Platform health, architecture metrics, ACL wiring, enforcement warn."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.architecture_metrics import ArchitectureMetricsStore, identified_couplings
from app.core.core_enforcement import resolve_enforcement_mode
from app.core.feature_flags import feature_flags
from app.shared.acl.booking_port import LegacyBookingAdapter


@pytest.fixture(autouse=True)
def reset_architecture_metrics():
    """Isola métricas arquiteturais entre testes."""
    ArchitectureMetricsStore.reset()
    yield
    ArchitectureMetricsStore.reset()


def test_feature_flags_all_disabled_by_default():
    """Nenhuma feature flag de migração ativa por padrão (R1-F2)."""
    flags = feature_flags.all_flags()
    assert flags["booking.core.enabled"]["enabled"] is False
    assert flags["ai.core.enabled"]["enabled"] is False
    assert flags["workflow.enabled"]["enabled"] is False
    assert flags["plugin.engine.enabled"]["enabled"] is False
    assert flags["legacy.telemetry.enabled"]["enabled"] is False


def test_enforcement_warn_in_development():
    """Enforcement efetivo warn em development com CORE_ENFORCEMENT_WARN_ENABLED."""
    assert resolve_enforcement_mode() == "warn"


def test_platform_health_endpoint(client):
    """GET /v1/platform/health retorna snapshot arquitetural."""
    response = client.get("/v1/platform/health")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1.20.1-r2-f2b"
    assert body["core"] == "healthy"
    assert "legacy" in body
    assert "plugins" in body
    assert "featureFlags" in body
    assert body["architecture"]["adrVersion"] == 8
    assert "telemetry" in body


def test_architecture_metrics_endpoint(client):
    """GET /v1/platform/architecture-metrics expõe couplings e readiness."""
    response = client.get("/v1/platform/architecture-metrics")
    assert response.status_code == 200
    body = response.json()
    assert "metrics" in body
    assert "couplings" in body
    assert len(body["couplings"]) >= 3
    assert "readiness" in body
    assert body["readiness"]["average"] >= 0


def test_plugin_registry_endpoint(client):
    """GET /v1/platform/plugin-registry documenta Beauty active."""
    response = client.get("/v1/platform/plugin-registry")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    beauty = next(p for p in body["plugins"] if p["plugin_id"] == "beauty")
    assert beauty["status"] == "active"
    assert "Booking" in beauty["dependencies"]["core_modules"]
    assert len(beauty["menus"]) >= 1


def test_readiness_score_endpoint(client):
    """GET /v1/platform/readiness-score retorna scoreboard."""
    response = client.get("/v1/platform/readiness-score")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert body["average"] >= 0
    names = {i["name"] for i in body["items"]}
    assert "hexagonal" in names
    assert "plugin_architecture" in names


def test_grafana_layers_dashboard_document(client):
    """GET /v1/platform/grafana/dashboard/layers."""
    response = client.get("/v1/platform/grafana/dashboard/layers")
    assert response.status_code == 200
    assert response.json()["uid"] == "coreflow-api-layers"


def test_architecture_metrics_store_http():
    """Store agrega percentuais legacy/core."""
    store = ArchitectureMetricsStore.get()
    store.record_http("legacy", 0.1, False)
    store.record_http("core", 0.05, False)
    snap = store.snapshot()
    assert snap["http"]["total"] == 2
    assert snap["http"]["legacy_percentage"] == 50.0
    assert snap["http"]["core_percentage"] == 50.0


def test_identified_couplings_static_audit():
    """Acoplamentos conhecidos documentados."""
    couplings = identified_couplings()
    sources = {c["source"] for c in couplings}
    assert "booking/commands/*" in sources


def test_acl_adapter_delegates_to_reservation_service(db):
    """LegacyBookingAdapter delega ao ReservationService sem alterar regras."""
    adapter = LegacyBookingAdapter(db)
    mock_agendamento = MagicMock()
    with patch(
        "app.services.reservation_service.ReservationService.criar_de_schema",
        return_value=mock_agendamento,
    ) as criar:
        result = adapter.create_booking_via_legacy(
            customer_id=1,
            tranca_id=2,
            service_image_id=3,
            scheduled_at="2026-07-01T10:00:00",
            company_id=1,
            notes="teste",
        )
    assert result is mock_agendamento
    criar.assert_called_once()
    assert ArchitectureMetricsStore.get().snapshot()["acl_invocations"] == 1


def test_acl_adapter_raises_when_core_booking_flag_enabled(db, monkeypatch):
    """booking.core.enabled sem path core levanta NotImplementedError."""
    monkeypatch.setattr(
        "app.core.feature_flags.settings.FEATURE_BOOKING_CORE_ENABLED",
        True,
    )
    adapter = LegacyBookingAdapter(db)
    with pytest.raises(NotImplementedError):
        adapter.create_booking_via_legacy(
            customer_id=1,
            tranca_id=2,
            service_image_id=3,
            scheduled_at="2026-07-01T10:00:00",
            company_id=1,
        )


def test_enforcement_warn_headers_on_legacy_write(client, monkeypatch):
    """POST legado em modo warn adiciona headers sem bloquear."""
    monkeypatch.setattr(
        "app.core.core_enforcement.settings.CORE_ENFORCEMENT_WARN_ENABLED",
        True,
    )
    monkeypatch.setattr(
        "app.core.core_enforcement.settings.CORE_ENFORCEMENT_MODE",
        "off",
    )
    monkeypatch.setattr(
        "app.core.core_enforcement.settings.APP_ENV",
        "development",
    )

    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient
    from app.core.core_enforcement import CoreEnforcementMiddleware

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/agenda/agendamentos", ok, methods=["POST"])])
    app.add_middleware(CoreEnforcementMiddleware, mode="warn")

    with TestClient(app) as tc:
        response = tc.post("/agenda/agendamentos", json={})
        assert response.status_code == 200
        assert response.headers.get("X-CoreFlow-Enforcement") == "warn"
        assert "Deprecation" in response.headers


def test_plugin_access_recorded_via_api(client):
    """GET /v1/plugins incrementa métrica de plugin."""
    response = client.get("/v1/plugins")
    assert response.status_code == 200
    snap = ArchitectureMetricsStore.get().snapshot()
    assert snap["plugins"].get("beauty", 0) >= 1


def test_legacy_telemetry_requires_flag(client, monkeypatch):
    """Telemetria HTTP desligada sem FEATURE_LEGACY_TELEMETRY_ENABLED."""
    monkeypatch.setattr(
        "app.core.feature_flags.settings.FEATURE_LEGACY_TELEMETRY_ENABLED",
        False,
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-CoreFlow-Layer") is None


def test_legacy_telemetry_with_flag(client, monkeypatch):
    """Telemetria ativa com flag habilitada."""
    monkeypatch.setattr(
        "app.core.feature_flags.settings.FEATURE_LEGACY_TELEMETRY_ENABLED",
        True,
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-CoreFlow-Layer") == "other"
