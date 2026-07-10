"""Testes CF-15 — CDN well-known export, Schema Registry Kafka, EAS mobile API."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.core.config import settings
from app.modules.mobile.application.well_known_export_service import WellKnownExportService
from app.shared.events.domain_event import DomainEvent
from app.shared.events.schema_registry import SchemaRegistryService


def test_well_known_cdn_cache_headers(client, monkeypatch):
    """Rotas .well-known incluem Cache-Control quando CDN habilitado."""
    monkeypatch.setattr(settings, "MOBILE_CDN_ENABLED", True)
    monkeypatch.setattr(settings, "MOBILE_WELL_KNOWN_CACHE_SECONDS", 3600)

    response = client.get("/.well-known/apple-app-site-association")
    assert response.status_code == 200
    assert "max-age=3600" in response.headers.get("cache-control", "")


def test_cdn_manifest(client):
    """GET /v1/mobile/cdn/manifest lista plugins multi-tenant."""
    response = client.get("/v1/mobile/cdn/manifest")
    assert response.status_code == 200
    body = response.json()
    assert body["multi_tenant"] is True
    assert len(body["plugins"]) >= 1


def test_well_known_export_to_disk(tmp_path):
    """Export grava AASA e assetlinks em diretório CDN."""
    service = WellKnownExportService(cdn_dir=tmp_path)
    paths = service.export_to_disk()

    assert Path(paths["apple_app_site_association"]).is_file()
    assert Path(paths["assetlinks"]).is_file()
    assert (tmp_path / ".well-known" / "apple-app-site-association").is_file()


def test_well_known_export_api(client, admin_headers):
    """POST /v1/mobile/well-known/export retorna paths (admin)."""
    with patch.object(WellKnownExportService, "export_to_disk") as mock_export:
        mock_export.return_value = {
            "apple_app_site_association": "/cdn/.well-known/apple-app-site-association",
            "assetlinks": "/cdn/.well-known/assetlinks.json",
        }
        response = client.post("/v1/mobile/well-known/export", headers=admin_headers)
    assert response.status_code == 200
    assert "apple_app_site_association" in response.json()


def test_schema_registry_lists_events():
    """Registry carrega schemas JSON de booking e payment."""
    registry = SchemaRegistryService()
    ids = {s["schema_id"] for s in registry.list_schemas()}
    assert "booking.approved.v1" in ids
    assert "payment.deposit.confirmed.v1" in ids


def test_schema_registry_validate_and_envelope():
    """Envelope inclui schema_id e valida campos required."""
    registry = SchemaRegistryService()
    event = DomainEvent(
        event_type="booking.approved",
        company_id=1,
        payload={"booking_id": 42, "legacy_agendamento_id": 42},
    )
    envelope = registry.envelope(event, outbox_id=7)
    assert envelope["schema_id"] == "booking.approved.v1"
    assert envelope["encoding"] == "json"
    assert envelope["outbox_id"] == 7

    parsed, outbox_id = registry.parse_envelope(envelope)
    assert parsed.event_type == "booking.approved"
    assert outbox_id == 7


def test_schema_registry_validate_missing_field():
    """Payload sem campo required levanta ValueError."""
    registry = SchemaRegistryService()
    with pytest.raises(ValueError, match="campos ausentes"):
        registry.validate_payload("booking.approved.v1", {})


def test_events_schemas_api(client):
    """API v1/events/schemas lista e detalha schemas."""
    list_resp = client.get("/v1/events/schemas")
    assert list_resp.status_code == 200
    assert any(s["schema_id"] == "booking.created.v1" for s in list_resp.json())

    detail = client.get("/v1/events/schemas/booking.created.v1")
    assert detail.status_code == 200
    assert detail.json()["title"] == "booking.created"


@patch("app.shared.events.kafka_adapter.KafkaEventAdapter._get_producer")
def test_kafka_publish_with_schema_envelope(mock_producer_factory, monkeypatch):
    """Kafka publish usa envelope schema quando registry habilitado."""
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_ENABLED", True)
    monkeypatch.setattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_producer.send.return_value = mock_future
    mock_producer_factory.return_value = mock_producer

    from app.shared.events.kafka_adapter import KafkaEventAdapter

    adapter = KafkaEventAdapter()
    event = DomainEvent(
        event_type="booking.approved",
        company_id=1,
        payload={"booking_id": 1},
    )
    adapter.publish(event, outbox_id=3)

    sent = mock_producer.send.call_args[0][1]
    assert sent["schema_id"] == "booking.approved.v1"
    assert sent["event"]["event_type"] == "booking.approved"
    adapter.close()
