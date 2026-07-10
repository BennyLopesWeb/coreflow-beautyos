"""Testes CF-20 — DLQ replay backoff, EAS rollout gradual, Terraform remote state."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_service import EasUpdateService
from app.modules.mobile.application.terraform_export_service import TerraformExportService
from app.shared.events.kafka_dlq import DlqReason, KafkaDlqService
from app.shared.events.kafka_dlq_replay import KafkaDlqReplayService


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-20."""
    plugin_registry.load_all()


def test_dlq_backoff_calculation():
    """Backoff exponencial respeita cap máximo."""
    assert KafkaDlqReplayService.calculate_backoff_seconds(0) == 30
    assert KafkaDlqReplayService.calculate_backoff_seconds(1) == 60
    assert KafkaDlqReplayService.calculate_backoff_seconds(10) == 3600


def test_dlq_replay_success(db, monkeypatch):
    """Replay bem-sucedido marca replayed_at."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    row = KafkaDlqService(db).record(
        raw_payload={"schema_id": "booking.approved.v1", "event": {"event_id": "x"}},
        error=ValueError("test"),
        reason=DlqReason.ENVELOPE_PARSE_ERROR,
    )
    with patch.object(KafkaDlqReplayService, "_publish_to_main_topic"):
        result = KafkaDlqReplayService(db).replay_one(row.id, force=True)
    assert result["status"] == "success"


def test_dlq_replay_failure_schedules_backoff(db, monkeypatch):
    """Falha incrementa attempts e agenda next_replay_at."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    row = KafkaDlqService(db).record(
        raw_payload={"bad": True},
        error=ValueError("fail"),
        reason=DlqReason.UNKNOWN,
    )
    with patch.object(
        KafkaDlqReplayService,
        "_publish_to_main_topic",
        side_effect=RuntimeError("kafka down"),
    ):
        result = KafkaDlqReplayService(db).replay_one(row.id, force=True)
    assert result["status"] == "failed"
    assert result["attempts"] == 1
    assert result["next_replay_at"] is not None


def test_dlq_replay_batch(db, monkeypatch):
    """replay_batch processa elegíveis."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    monkeypatch.setattr(settings, "KAFKA_DLQ_REPLAY_ENABLED", True)
    KafkaDlqService(db).record(
        raw_payload={"event": {"event_id": "1"}},
        error=ValueError("x"),
        reason=DlqReason.UNKNOWN,
    )
    with patch.object(KafkaDlqReplayService, "_publish_to_main_topic"):
        result = KafkaDlqReplayService(db).replay_batch(limit=5, force=True)
    assert result["processed"] >= 1
    assert result["counts"]["success"] >= 1


def test_dlq_replay_auto_api(client, db, admin_headers, monkeypatch):
    """POST /v1/events/dlq/replay-auto executa batch."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    KafkaDlqService(db).record(
        raw_payload={"event": {"event_id": "2"}},
        error=ValueError("x"),
        reason=DlqReason.UNKNOWN,
    )
    with patch.object(KafkaDlqReplayService, "_publish_to_main_topic"):
        response = client.post(
            "/v1/events/dlq/replay-auto?limit=5&force=true&mode=republish",
            headers=admin_headers,
        )
    assert response.status_code == 200
    assert response.json()["counts"]["success"] >= 1


def test_eas_rollout_plan_sports():
    """SportsOS rollout 50% gera stages aplicáveis."""
    plan = EasUpdateService().build_rollout_plan("sports", target_percentage=50)
    assert plan["current_stage"] == 50
    assert 50 in plan["applicable_stages"]
    assert any("--rollout-percentage 50" in cmd for cmd in plan["commands"])


def test_eas_rollout_command():
    """update_command inclui --rollout-percentage em production."""
    cmd = EasUpdateService().update_command(
        "clinic", "production", "OTA", rollout_percentage=25
    )
    assert "--rollout-percentage 25" in cmd


def test_eas_rollout_api(client):
    """GET /v1/mobile/eas/update/rollout/{plugin_id}."""
    response = client.get("/v1/mobile/eas/update/rollout/sports?target_percentage=50")
    assert response.status_code == 200
    assert response.json()["target_percentage"] == 50


def test_terraform_backend_config():
    """backend_config monta remote state S3."""
    cfg = TerraformExportService().backend_config("dev")
    assert cfg["backend"] == "s3"
    assert "cdn/dev/terraform.tfstate" in cfg["key"]


def test_terraform_export_backend(tmp_path):
    """export_backend_config grava backend.hcl."""
    service = TerraformExportService(terraform_dir=tmp_path)
    result = service.export_backend_config("dev")
    backend_path = tmp_path / "environments" / "dev" / "backend.hcl"
    assert backend_path.is_file()
    assert "bucket" in backend_path.read_text()


def test_terraform_backend_api(client):
    """GET /v1/mobile/cdn/terraform/backend retorna config."""
    response = client.get("/v1/mobile/cdn/terraform/backend?environment=dev")
    assert response.status_code == 200
    assert response.json()["bucket"] == settings.TERRAFORM_STATE_BUCKET
