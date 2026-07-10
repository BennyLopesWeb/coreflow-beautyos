"""Testes CF-18 — EAS Submit, Avro evolution, CloudFront behaviors."""
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.cloudfront_behaviors_service import CloudFrontBehaviorsService
from app.modules.mobile.application.eas_submit_service import EasSubmitService
from app.shared.events.avro_evolution_service import AvroEvolutionService
from app.shared.events.confluent_schema_registry import ConfluentSchemaRegistryClient


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-18."""
    plugin_registry.load_all()


def test_eas_submit_sports_config():
    """SportsOS tem ascAppId dedicado no submit."""
    cfg = EasSubmitService().submit_config("sports")
    assert cfg["ios"]["ascAppId"] == "1000000002"
    assert cfg["android"]["serviceAccountKeyPath"].endswith("sports-play-service-account.json")
    assert cfg["profile_key"] == "sports-production"


def test_eas_submit_generate_file(tmp_path):
    """generate_submit_file grava eas.submit.json."""
    doc = EasSubmitService(frontend_dir=tmp_path).generate_submit_file()
    assert (tmp_path / "eas.submit.json").is_file()
    assert "sports-production" in doc["submit"]


def test_eas_submit_profiles_api(client):
    """GET /v1/mobile/eas/submit/profiles lista perfis."""
    response = client.get("/v1/mobile/eas/submit/profiles")
    assert response.status_code == 200
    keys = [p["submit_key"] for p in response.json()]
    assert "clinic-production" in keys


def test_avro_backward_compatible_v1_v2():
    """booking.approved v2 é backward compatible com v1."""
    service = AvroEvolutionService()
    result = service.check_backward_compatible(
        "booking.approved.v1",
        "booking.approved.v2",
    )
    assert result["compatible"] is True
    assert "approved_by" in result["new_fields"]


def test_avro_evolution_report():
    """Relatório inclui booking.approved evoluído."""
    report = AvroEvolutionService().evolution_report()
    booking = next(r for r in report if r["event_type"] == "booking.approved")
    assert booking["evolved"] is True
    assert booking["compatible"] is True


def test_avro_versions_api(client):
    """GET /v1/events/schemas/avro/booking.approved/versions."""
    response = client.get("/v1/events/schemas/avro/booking.approved/versions")
    assert response.status_code == 200
    versions = [v["schema_id"] for v in response.json()]
    assert "booking.approved.v1" in versions
    assert "booking.approved.v2" in versions


def test_avro_check_compatibility_api(client):
    """POST check-compatibility retorna compatible."""
    response = client.post(
        "/v1/events/schemas/avro/check-compatibility",
        params={
            "old_schema_id": "booking.approved.v1",
            "new_schema_id": "booking.approved.v2",
        },
    )
    assert response.status_code == 200
    assert response.json()["compatible"] is True


def test_register_evolved_avro_confluent(monkeypatch):
    """register_evolved_schema valida e registra no Confluent."""
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_MODE", "confluent")

    with patch.object(
        ConfluentSchemaRegistryClient,
        "check_compatibility",
        return_value={"is_compatible": True},
    ):
        with patch.object(
            ConfluentSchemaRegistryClient,
            "register_avro_schema",
            return_value=101,
        ):
            result = AvroEvolutionService().register_evolved_schema("booking.approved")
    assert result["confluent_schema_id"] == 101
    assert result["schema_id"] == "booking.approved.v2"


def test_cloudfront_behaviors_per_plugin():
    """Cada plugin tem PathPattern dedicado."""
    service = CloudFrontBehaviorsService()
    beauty = service.behavior_for_plugin("beauty")
    sports = service.behavior_for_plugin("sports")
    assert beauty["PathPattern"] == "/beauty/.well-known/*"
    assert sports["cdn_host"] == "sports.coreflow.app"


def test_cloudfront_distribution_config():
    """Distribution inclui aliases de todos plugins."""
    config = CloudFrontBehaviorsService().distribution_config()
    assert "sports.coreflow.app" in config["Aliases"]
    assert len(config["CacheBehaviors"]) >= 3


def test_cloudfront_export(tmp_path):
    """export_to_disk grava cloudfront-behaviors.json."""
    service = CloudFrontBehaviorsService(infra_dir=tmp_path)
    paths = service.export_to_disk()
    assert Path(paths["cloudfront_behaviors"]).is_file()


def test_cloudfront_behaviors_api(client):
    """GET /v1/mobile/cdn/cloudfront-behaviors retorna config."""
    response = client.get("/v1/mobile/cdn/cloudfront-behaviors")
    assert response.status_code == 200
    assert "CacheBehaviors" in response.json()
