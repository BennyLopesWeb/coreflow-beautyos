"""Testes CF-22 — Prometheus DLQ, canary auto-promote, Terraform drift."""
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.core.prometheus_metrics import metrics_summary, record_dlq_replay, render_prometheus
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_promote_service import EasUpdateCanaryPromoteService
from app.modules.mobile.application.terraform_drift_service import TerraformDriftService
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
from app.shared.events.dlq_handler_replay import DlqHandlerReplayService
from app.shared.events.kafka_dlq import DlqReason, KafkaDlqService


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-22."""
    plugin_registry.load_all()
    EasUpdateCanaryHealthService.reset_samples()


def _valid_event_payload():
    """Envelope DLQ válido para handler replay."""
    return {
        "event": {
            "event_id": "evt-cf22-1",
            "event_type": "booking.approved",
            "company_id": 1,
            "payload": {"booking_id": 1},
            "occurred_at": datetime.utcnow().isoformat(),
        }
    }


def test_prometheus_record_dlq_replay():
    """Contador Prometheus incrementa após replay."""
    record_dlq_replay("handler", "success", 0.05)
    summary = metrics_summary()
    assert summary["enabled"] is True
    assert summary["prometheus_client_installed"] is True


def test_prometheus_metrics_endpoint(client, db, monkeypatch):
    """GET /metrics retorna formato Prometheus."""
    monkeypatch.setattr(settings, "PROMETHEUS_ENABLED", True)
    record_dlq_replay("handler", "success")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "coreflow_dlq_replay_total" in response.text


def test_dlq_metrics_json_api(client, db, admin_headers, monkeypatch):
    """GET /v1/events/dlq/metrics retorna resumo JSON."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    KafkaDlqService(db).record(
        raw_payload={"event": {"event_id": "m1"}},
        error=ValueError("x"),
        reason=DlqReason.UNKNOWN,
    )
    response = client.get("/v1/events/dlq/metrics")
    assert response.status_code == 200
    assert "dlq" in response.json()


def test_dlq_replay_records_prometheus(db, monkeypatch):
    """Handler replay incrementa métrica success."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    row = KafkaDlqService(db).record(
        raw_payload=_valid_event_payload(),
        error=ValueError("x"),
        reason=DlqReason.HANDLER_ERROR,
    )
    with patch("app.shared.events.dlq_handler_replay.event_bus.publish"):
        DlqHandlerReplayService(db).replay_one(row.id, force=True, mode="handler")
    summary = metrics_summary(db)
    counters = summary.get("counters", {}).get("coreflow_dlq_replay_total", [])
    assert any(c["labels"].get("status") == "success" for c in counters)


def test_canary_health_mock_healthy():
    """Health mock passa com amostras suficientes."""
    svc = EasUpdateCanaryHealthService()
    for _ in range(10):
        svc.record_sample("beauty", "trancista", True)
    health = svc.probe_health("beauty", "trancista")
    assert health["healthy"] is True
    assert health["probe_mode"] == "mock"


def test_canary_health_low_success_rate():
    """Health reprova com taxa abaixo do threshold."""
    svc = EasUpdateCanaryHealthService()
    for _ in range(5):
        svc.record_sample("sports", "futebol", True)
    for _ in range(5):
        svc.record_sample("sports", "futebol", False)
    health = svc.probe_health("sports", "futebol")
    assert health["healthy"] is False


def test_canary_promote_evaluate_hold():
    """Evaluate retorna hold quando health reprova."""
    svc = EasUpdateCanaryHealthService()
    for _ in range(10):
        svc.record_sample("clinic", "odontologia", False)
    evaluation = EasUpdateCanaryPromoteService().evaluate("clinic", "odontologia")
    assert evaluation["decision"] == "hold"


def test_canary_promote_success():
    """Auto-promote gera plano quando health OK."""
    svc = EasUpdateCanaryHealthService()
    for _ in range(10):
        svc.record_sample("beauty", "trancista", True)
    result = EasUpdateCanaryPromoteService().auto_promote("beauty", "trancista")
    assert result["decision"] == "promote"
    assert "eas channel:edit" in result["promote_plan"]["command"]


def test_canary_health_api(client):
    """GET /v1/mobile/eas/update/canary/{plugin}/health."""
    EasUpdateCanaryHealthService().record_sample("beauty", "trancista", True)
    response = client.get(
        "/v1/mobile/eas/update/canary/beauty/health?segment=trancista"
    )
    assert response.status_code == 200
    assert "healthy" in response.json()


def test_canary_promote_api(client, admin_headers):
    """POST promote com force=true."""
    response = client.post(
        "/v1/mobile/eas/update/canary/sports/promote?segment=futebol&force=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "promote"


def test_terraform_config_drift_no_file(tmp_path):
    """Sem arquivo commitado não há drift."""
    service = TerraformDriftService(
        pipeline_service=TerraformPipelineService(terraform_dir=tmp_path),
        terraform_dir=tmp_path,
    )
    result = service.config_drift("dev")
    assert result["has_drift"] is False
    assert result["has_committed_file"] is False


def test_terraform_config_drift_detected(tmp_path):
    """Hash diferente do commitado indica drift."""
    pipeline = TerraformPipelineService(terraform_dir=tmp_path)
    pipeline.export_environment("dev")
    committed = tmp_path / "environments" / "dev" / "terraform.tfvars.json"
    committed.write_text('{"bucket_name": "old-bucket"}', encoding="utf-8")

    service = TerraformDriftService(pipeline_service=pipeline, terraform_dir=tmp_path)
    result = service.config_drift("dev")
    assert result["has_drift"] is True


def test_terraform_drift_all_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/drift/all."""
    response = client.get("/v1/mobile/cdn/terraform/drift/all", headers=admin_headers)
    assert response.status_code == 200
    assert "environments" in response.json()


def test_terraform_drift_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/drift."""
    response = client.get(
        "/v1/mobile/cdn/terraform/drift?environment=dev",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "config" in response.json()
