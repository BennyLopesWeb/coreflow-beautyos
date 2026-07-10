"""Testes CF-19 — EAS Update OTA, Kafka DLQ, Terraform CDN."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_service import EasUpdateService
from app.modules.mobile.application.terraform_export_service import TerraformExportService
from app.shared.events.domain_event import DomainEvent
from app.shared.events.kafka_dlq import DlqReason, KafkaDlqService
from app.shared.events.kafka_adapter import KafkaEventAdapter
from app.shared.events.schema_registry import SchemaRegistryService


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-19."""
    plugin_registry.load_all()


def test_eas_update_sports_channel():
    """SportsOS tem canal OTA dedicado."""
    profile = EasUpdateService().build_update_profile("sports", "preview")
    assert profile["channel"] == "sports-preview"
    assert profile["update_key"] == "sports-preview"


def test_eas_update_generate_file(tmp_path):
    """generate_update_file grava eas.update.json."""
    doc = EasUpdateService(frontend_dir=tmp_path).generate_update_file()
    assert (tmp_path / "eas.update.json").is_file()
    assert "sports-production" in doc["update"]


def test_eas_update_channels_api(client):
    """GET /v1/mobile/eas/update/channels lista OTA."""
    response = client.get("/v1/mobile/eas/update/channels")
    assert response.status_code == 200
    keys = [p["update_key"] for p in response.json()]
    assert "beauty-preview" in keys


def test_kafka_dlq_record(db):
    """KafkaDlqService persiste mensagem incompatível."""
    service = KafkaDlqService(db)
    row = service.record(
        raw_payload={"bad": "payload"},
        error=ValueError("schema inválido"),
        reason=DlqReason.SCHEMA_INCOMPATIBLE,
        event_type="booking.approved",
    )
    assert row.id is not None
    assert row.error_type == DlqReason.SCHEMA_INCOMPATIBLE


def test_kafka_dlq_stats(db):
    """stats agrega entradas DLQ."""
    service = KafkaDlqService(db)
    service.record(
        raw_payload={"x": 1},
        error=RuntimeError("handler fail"),
        reason=DlqReason.HANDLER_ERROR,
    )
    stats = service.stats()
    assert stats["total"] >= 1
    assert "handler_error" in stats["by_reason"]


def test_kafka_consume_sends_to_dlq(db, monkeypatch):
    """consume_one envia mensagem inválida à DLQ em vez de propagar."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", True)
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_ENABLED", True)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: db)

    mock_message = MagicMock()
    mock_message.value = {"invalid": "envelope"}
    mock_message.partition = 0
    mock_message.offset = 42

    mock_consumer = MagicMock()
    mock_consumer.__iter__ = MagicMock(return_value=iter([mock_message]))

    adapter = KafkaEventAdapter()
    with patch.object(KafkaDlqService, "_publish_to_kafka"):
        with patch.object(adapter, "_get_consumer", return_value=mock_consumer):
            handled = adapter.consume_one(lambda e, o: None)

    assert handled is True
    stats = KafkaDlqService(db).stats()
    assert stats["total"] >= 1


def test_dlq_api(client, db, monkeypatch):
    """GET /v1/events/dlq retorna entradas."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    KafkaDlqService(db).record(
        raw_payload={"test": True},
        error=ValueError("test"),
        reason=DlqReason.UNKNOWN,
    )
    response = client.get("/v1/events/dlq")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_dlq_stats_api(client, db, monkeypatch):
    """GET /v1/events/dlq/stats retorna agregados."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    KafkaDlqService(db).record(
        raw_payload={"test": True},
        error=ValueError("test"),
        reason=DlqReason.UNKNOWN,
    )
    response = client.get("/v1/events/dlq/stats")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_terraform_export_tfvars(tmp_path):
    """TerraformExportService gera tfvars com tenant_behaviors."""
    service = TerraformExportService(terraform_dir=tmp_path)
    result = service.export_tfvars("dev")
    tfvars_path = Path(result["terraform_tfvars"])
    assert tfvars_path.is_file()
    doc = __import__("json").loads(tfvars_path.read_text())
    assert len(doc["tenant_behaviors"]) >= 3


def test_terraform_export_api(client, admin_headers):
    """POST /v1/mobile/cdn/terraform/export gera tfvars."""
    response = client.post(
        "/v1/mobile/cdn/terraform/export?environment=dev",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "terraform_tfvars" in response.json()
