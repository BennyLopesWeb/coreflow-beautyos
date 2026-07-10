"""Testes CF-17 — EAS white-label, Avro completo, CDN S3 sync."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.cdn_s3_sync_service import CdnS3SyncService
from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService
from app.shared.events.avro_codec import AvroEventCodec
from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient
from app.shared.events.domain_event import DomainEvent
from app.shared.events.schema_registry import SchemaRegistryService


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-17."""
    plugin_registry.load_all()


def test_eas_whitelabel_sports_bundle():
    """SportsOS tem bundle ID white-label dedicado."""
    cfg = EasWhitelabelService().mobile_eas_config("sports")
    assert cfg["ios_bundle_id"] == "com.coreflow.sports"
    assert cfg["android_package"] == "com.coreflow.sports"
    assert cfg["expo_slug"] == "sportsos"


def test_eas_whitelabel_profile_key():
    """Perfil EAS usa chave {plugin}-{profile}."""
    built = EasWhitelabelService().build_profile("clinic", "production")
    assert built["profile_key"] == "clinic-production"
    assert built["profile"]["ios"]["bundleIdentifier"] == "com.coreflow.clinic"
    assert built["profile"]["env"]["EXPO_PUBLIC_PLUGIN_ID"] == "clinic"


def test_eas_generate_plugins_file(tmp_path):
    """generate_plugins_file grava eas.plugins.json."""
    service = EasWhitelabelService(frontend_dir=tmp_path)
    doc = service.generate_plugins_file()
    assert (tmp_path / "eas.plugins.json").is_file()
    assert "beauty" in doc["plugins"]
    assert "beauty-preview" in doc["build"]


def test_eas_profiles_api(client):
    """GET /v1/mobile/eas/profiles lista perfis white-label."""
    response = client.get("/v1/mobile/eas/profiles?profile=preview")
    assert response.status_code == 200
    profiles = response.json()
    assert any(p["profile_key"] == "sports-preview" for p in profiles)


def test_eas_app_config_overlay(client):
    """GET /v1/mobile/eas/app-config/{plugin_id} retorna overlay."""
    response = client.get("/v1/mobile/eas/app-config/beauty")
    assert response.status_code == 200
    body = response.json()
    assert body["expo"]["slug"] == "beautyos"


def test_avro_coverage_complete():
    """Todos os JSON Schemas têm par Avro."""
    coverage = SchemaRegistryService().list_avro_coverage()
    assert len(coverage) >= 5
    assert all(item["complete"] for item in coverage)


@pytest.mark.parametrize(
    "event_type,payload,schema_id",
    [
        ("booking.approved", {"booking_id": 1}, "booking.approved.v1"),
        ("booking.created", {"booking_id": 2}, "booking.created.v1"),
        ("booking.rejected", {"booking_id": 3, "reason": "no slot"}, "booking.rejected.v1"),
        ("reservation.created", {"reservation_id": 4}, "reservation.created.v1"),
        (
            "payment.deposit.confirmed",
            {"agendamento_id": 5},
            "payment.deposit.confirmed.v1",
        ),
    ],
)
def test_avro_encode_all_events(event_type, payload, schema_id):
    """AvroEventCodec codifica todos os eventos registrados."""
    pytest.importorskip("fastavro")
    registry = SchemaRegistryService()
    event = DomainEvent(event_type=event_type, company_id=1, payload=payload)
    record = registry.build_avro_record(event)
    wire = AvroEventCodec().encode(schema_id, record, confluent_schema_id=1)
    assert isinstance(wire, bytes)
    assert wire[0] == 0


def test_avro_schemas_api(client):
    """GET /v1/events/schemas/avro lista .avsc."""
    response = client.get("/v1/events/schemas/avro")
    assert response.status_code == 200
    ids = {item["schema_id"] for item in response.json()}
    assert "booking.created.v1" in ids
    assert "payment.deposit.confirmed.v1" in ids


def test_avro_coverage_api(client):
    """GET /v1/events/schemas/avro/coverage retorna cobertura 100%."""
    response = client.get("/v1/events/schemas/avro/coverage")
    assert response.status_code == 200
    assert all(item["complete"] for item in response.json())


def test_register_all_avro_confluent(monkeypatch):
    """register_all_avro_to_confluent registra todos subjects."""
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_MODE", "confluent")

    with patch.object(ConfluentSchemaRegistryClient, "get_latest_schema_id", return_value=None):
        with patch.object(
            ConfluentSchemaRegistryClient,
            "register_avro_schema",
            side_effect=lambda subject, schema: hash(subject) % 1000,
        ):
            results = SchemaRegistryService().register_all_avro_to_confluent()
    assert len(results) >= 5


def test_cdn_s3_sync_dry_run(tmp_path):
    """sync_all em dry-run lista arquivos sem boto3."""
    plugin_registry.load_all()
    service = CdnS3SyncService(cdn_dir=tmp_path)
    result = service.sync_all(dry_run=True)
    assert result["dry_run"] is True
    assert result["uploaded_count"] >= 4


@patch("app.modules.mobile.application.cdn_s3_sync_service.CdnS3SyncService._s3_client")
def test_cdn_s3_sync_upload(mock_s3_client, tmp_path, monkeypatch):
    """sync_all faz put_object quando S3 habilitado."""
    monkeypatch.setattr(settings, "CDN_S3_DRY_RUN", False)
    monkeypatch.setattr(settings, "CDN_S3_ENABLED", True)
    monkeypatch.setattr(settings, "CDN_S3_BUCKET", "coreflow-cdn-test")

    mock_client = MagicMock()
    mock_s3_client.return_value = mock_client

    plugin_registry.load_all()
    service = CdnS3SyncService(cdn_dir=tmp_path)
    result = service.sync_all(dry_run=False)
    assert result["dry_run"] is False
    assert result["uploaded_count"] >= 4
    assert mock_client.put_object.called
