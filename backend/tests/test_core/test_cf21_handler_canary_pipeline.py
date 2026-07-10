"""Testes CF-21 — DLQ handler replay, EAS canary, Terraform pipeline."""
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_service import EasUpdateCanaryService
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
from app.shared.events.dlq_handler_replay import DlqHandlerReplayService
from app.shared.events.kafka_dlq import DlqReason, KafkaDlqService
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus


@pytest.fixture(autouse=True)
def load_plugins():
    """Carrega plugins antes de cada teste CF-21."""
    plugin_registry.load_all()


def _valid_event_payload(outbox_id=None):
    """Monta envelope DLQ válido para handler replay."""
    return {
        "event": {
            "event_id": "evt-cf21-1",
            "event_type": "booking.approved",
            "company_id": 1,
            "payload": {"booking_id": 42},
            "occurred_at": datetime.utcnow().isoformat(),
        },
        "outbox_id": outbox_id,
    }


def test_dlq_handler_replay_success(db, monkeypatch):
    """Replay handler-aware publica no event_bus e marca replayed_at."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    row = KafkaDlqService(db).record(
        raw_payload=_valid_event_payload(),
        error=ValueError("handler fail"),
        reason=DlqReason.HANDLER_ERROR,
    )
    with patch("app.shared.events.dlq_handler_replay.event_bus.publish") as publish:
        result = DlqHandlerReplayService(db).replay_one(row.id, force=True, mode="handler")
    assert result["status"] == "success"
    assert result["mode"] == "handler"
    publish.assert_called_once()


def test_dlq_handler_replay_marks_outbox(db, monkeypatch):
    """Handler replay marca outbox como PROCESSED quando outbox_id presente."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    outbox = CoreEventOutbox(
        event_id="outbox-cf21-1",
        event_type="booking.approved",
        company_id=1,
        payload='{"booking_id": 1}',
        status=OutboxStatus.PENDING,
    )
    db.add(outbox)
    db.commit()
    db.refresh(outbox)

    row = KafkaDlqService(db).record(
        raw_payload=_valid_event_payload(outbox_id=outbox.id),
        error=ValueError("retry"),
        reason=DlqReason.HANDLER_ERROR,
    )
    with patch("app.shared.events.dlq_handler_replay.event_bus.publish"):
        DlqHandlerReplayService(db).replay_one(row.id, force=True, mode="handler")

    db.refresh(outbox)
    assert outbox.status == OutboxStatus.PROCESSED
    assert outbox.processed_at is not None


def test_dlq_handler_replay_api(client, db, admin_headers, monkeypatch):
    """POST replay-auto com mode=handler."""
    monkeypatch.setattr(settings, "KAFKA_DLQ_ENABLED", False)
    KafkaDlqService(db).record(
        raw_payload=_valid_event_payload(),
        error=ValueError("x"),
        reason=DlqReason.HANDLER_ERROR,
    )
    with patch("app.shared.events.dlq_handler_replay.event_bus.publish"):
        response = client.post(
            "/v1/events/dlq/replay-auto?limit=5&force=true&mode=handler",
            headers=admin_headers,
        )
    assert response.status_code == 200
    assert response.json()["mode"] == "handler"
    assert response.json()["counts"]["success"] >= 1


def test_eas_canary_plan_beauty():
    """Plano canary gera channel por segmento."""
    plan = EasUpdateCanaryService().build_canary_plan("beauty", "trancista")
    assert plan["canary_channel"] == "beauty-canary-trancista"
    assert plan["rollout_percentage"] == 10
    assert "--rollout-percentage 10" in plan["command"]
    assert plan["env"]["EXPO_PUBLIC_CANARY_SEGMENT"] == "trancista"


def test_eas_canary_invalid_segment():
    """Segmento inválido levanta ValueError."""
    with pytest.raises(ValueError, match="inválido"):
        EasUpdateCanaryService().build_canary_plan("sports", "trancista")


def test_eas_canary_api(client):
    """GET /v1/mobile/eas/update/canary/{plugin_id}."""
    response = client.get(
        "/v1/mobile/eas/update/canary/sports?segment=futebol&percentage=20"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["segment"] == "futebol"
    assert body["rollout_percentage"] == 20
    assert "sports-canary-futebol" in body["canary_channel"]


def test_eas_canary_segments_api(client):
    """GET segments canary por plugin."""
    response = client.get("/v1/mobile/eas/update/canary/sports/segments")
    assert response.status_code == 200
    assert "futebol" in response.json()


def test_terraform_pipeline_tfvars_overrides(tmp_path):
    """tfvars por ambiente aplica suffix e price class."""
    service = TerraformPipelineService(terraform_dir=tmp_path)
    dev = service.tfvars_for_environment("dev")
    prod = service.tfvars_for_environment("prod")
    assert dev["bucket_name"].endswith("-dev")
    assert prod["bucket_name"].endswith("-prod")
    assert prod["cloudfront_price_class"] == "PriceClass_All"
    assert prod["tags"]["Environment"] == "prod"


def test_terraform_pipeline_export_all(tmp_path):
    """export_all_environments grava tfvars e backend por ambiente."""
    service = TerraformPipelineService(terraform_dir=tmp_path)
    results = service.export_all_environments()
    assert len(results) == 3
    for env in ("dev", "staging", "prod"):
        env_dir = tmp_path / "environments" / env
        assert (env_dir / "terraform.tfvars.json").is_file()
        assert (env_dir / "backend.hcl").is_file()


def test_terraform_pipeline_manifest():
    """pipeline_manifest define ordem dev → staging → prod."""
    manifest = TerraformPipelineService().pipeline_manifest()
    assert manifest["promotion_order"] == ["dev", "staging", "prod"]
    assert manifest["stages"][1]["environment"] == "staging"
    assert manifest["stages"][2]["require_approval"] is True


def test_terraform_pipeline_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/pipeline."""
    response = client.get("/v1/mobile/cdn/terraform/pipeline")
    assert response.status_code == 200
    assert "stages" in response.json()


def test_terraform_pipeline_export_api(client, admin_headers, tmp_path, monkeypatch):
    """POST pipeline/export grava manifest."""
    monkeypatch.setattr(
        "app.modules.mobile.application.terraform_pipeline_service.TERRAFORM_DIR",
        tmp_path,
    )
    response = client.post(
        "/v1/mobile/cdn/terraform/pipeline/export",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "pipeline_manifest" in response.json()
    assert len(response.json()["environments"]) == 3
