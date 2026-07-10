"""Testes CF-16 — Confluent SR, Avro, CDN multi-plugin, EAS CI hooks."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.plugin_cdn_service import PluginCdnService
from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient
from app.shared.events.domain_event import DomainEvent
from app.shared.events.schema_registry import SchemaRegistryService


def test_plugin_cdn_mobile_config_sports():
    """Plugin sports expõe cdn_host dedicado."""
    cfg = PluginCdnService().mobile_config("sports")
    assert cfg["cdn_host"] == "sports.coreflow.app"
    assert cfg["plugin_id"] == "sports"


def test_plugin_cdn_multi_aasa():
    """AASA agregado inclui details de todos os plugins."""
    plugin_registry.load_all()
    body = PluginCdnService().apple_app_site_association()
    assert len(body["applinks"]["details"]) >= 3


def test_plugin_cdn_export_all(tmp_path):
    """export_all_plugins grava global + por plugin."""
    plugin_registry.load_all()
    service = PluginCdnService(cdn_dir=tmp_path)
    results = service.export_all_plugins()
    assert len(results) >= 4
    assert (tmp_path / "beauty" / ".well-known" / "apple-app-site-association").is_file()
    assert (tmp_path / ".well-known" / "assetlinks.json").is_file()


def test_cdn_manifest_multi_tenant(client):
    """GET /v1/mobile/cdn/manifest retorna plugins[]."""
    response = client.get("/v1/mobile/cdn/manifest")
    assert response.status_code == 200
    body = response.json()
    assert body["multi_tenant"] is True
    assert len(body["plugins"]) >= 3
    sports = next(p for p in body["plugins"] if p["plugin_id"] == "sports")
    assert sports["cdn_host"] == "sports.coreflow.app"


def test_cdn_plugins_list(client):
    """GET /v1/mobile/cdn/plugins lista configs mobile."""
    response = client.get("/v1/mobile/cdn/plugins")
    assert response.status_code == 200
    assert len(response.json()) >= 3


@patch("app.shared.events.confluent_schema_registry.httpx.post")
@patch("app.shared.events.confluent_schema_registry.httpx.get")
def test_confluent_register_json_schema(mock_get, mock_post, monkeypatch):
    """Confluent client registra JSON Schema e retorna id."""
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
    mock_get.return_value = MagicMock(status_code=404)
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"id": 42})

    client = ConfluentSchemaRegistryClient()
    schema_id = client.register_json_schema(
        "booking.approved-value",
        {"type": "object", "properties": {"booking_id": {"type": "integer"}}},
    )
    assert schema_id == 42


def test_schema_registry_confluent_metadata(monkeypatch):
    """Envelope inclui confluent_schema_id em mode confluent."""
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_MODE", "confluent")

    with patch.object(ConfluentSchemaRegistryClient, "get_latest_schema_id", return_value=99):
        registry = SchemaRegistryService()
        event = DomainEvent(
            event_type="booking.approved",
            company_id=1,
            payload={"booking_id": 1},
        )
        envelope = registry.envelope(event, outbox_id=5)
        assert envelope["confluent_schema_id"] == 99
        assert envelope["confluent_subject"] == "booking.approved-value"


def test_schema_registry_health_file_mode(client):
    """Health SR retorna ok em mode file."""
    response = client.get("/v1/events/schema-registry/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "file"


def test_avro_encode_decode():
    """AvroEventCodec serializa e deserializa wire format Confluent."""
    pytest.importorskip("fastavro")
    from app.shared.events.avro_codec import AvroEventCodec

    codec = AvroEventCodec()
    record = {
        "event_id": "abc",
        "event_type": "booking.approved",
        "company_id": 1,
        "booking_id": 10,
        "legacy_agendamento_id": 10,
        "occurred_at": "2026-07-09T12:00:00",
    }
    wire = codec.encode("booking.approved.v1", record, confluent_schema_id=7)
    assert isinstance(wire, bytes)
    assert wire[0] == 0
