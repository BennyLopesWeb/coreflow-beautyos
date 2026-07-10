"""Testes CF-23 — Grafana dashboards, canary rollback, Terraform OPA."""
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_promote_service import EasUpdateCanaryPromoteService
from app.modules.mobile.application.eas_update_canary_rollback_service import EasUpdateCanaryRollbackService
from app.modules.mobile.application.terraform_policy_service import TerraformPolicyService
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
from app.modules.observability.application.grafana_dashboard_service import GrafanaDashboardService


@pytest.fixture(autouse=True)
def reset_state(db, monkeypatch):
    """Reseta estado canary entre testes CF-23 (in-memory)."""
    monkeypatch.setattr(settings, "MOBILE_EAS_UPDATE_CANARY_PERSIST_DB", False)
    plugin_registry.load_all()
    EasUpdateCanaryHealthService.reset_samples()
    EasUpdateCanaryRollbackService.reset_state(db=db)


def test_grafana_dashboard_document():
    """Dashboard DLQ contém panels Prometheus."""
    doc = GrafanaDashboardService().dlq_dashboard_document()
    assert doc["uid"] == "coreflow-dlq"
    assert len(doc["panels"]) >= 5
    assert any("coreflow_dlq_pending" in str(p) for p in doc["panels"])


def test_grafana_export_all(tmp_path):
    """export_all grava dashboard e provisioning."""
    service = GrafanaDashboardService(grafana_dir=tmp_path)
    paths = service.export_all()
    assert (tmp_path / "dashboards" / "coreflow-dlq.json").is_file()
    assert (tmp_path / "provisioning" / "datasources" / "prometheus.yaml").is_file()
    assert "dashboard" in paths


def test_grafana_dashboard_api(client):
    """GET /v1/events/grafana/dashboard/dlq."""
    response = client.get("/v1/events/grafana/dashboard/dlq")
    assert response.status_code == 200
    assert response.json()["dashboard_uid"] == "coreflow-dlq"


def test_grafana_export_api(client, admin_headers, tmp_path, monkeypatch):
    """POST export grafana dashboard."""
    monkeypatch.setattr(
        "app.modules.observability.application.grafana_dashboard_service.GRAFANA_DIR",
        tmp_path,
    )
    response = client.post(
        "/v1/events/grafana/dashboard/dlq/export",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "dashboard" in response.json()


def test_canary_rollback_evaluate_no_promotion():
    """Evaluate retorna noop sem promoção registrada."""
    result = EasUpdateCanaryRollbackService().evaluate("beauty", "trancista")
    assert result["decision"] == "noop"


def test_canary_rollback_on_degradation():
    """Rollback quando success_rate cai após promote."""
    health_svc = EasUpdateCanaryHealthService()
    rollback_svc = EasUpdateCanaryRollbackService()
    rollback_svc.record_promotion("beauty", "trancista", previous_branch="beauty-production")

    for _ in range(10):
        health_svc.record_sample("beauty", "trancista", False)

    evaluation = rollback_svc.evaluate("beauty", "trancista")
    assert evaluation["decision"] == "rollback"
    assert "eas channel:edit" in evaluation["rollback_plan"]["command"]


def test_canary_rollback_hold_when_healthy():
    """Hold quando health acima do rollback threshold."""
    health_svc = EasUpdateCanaryHealthService()
    rollback_svc = EasUpdateCanaryRollbackService()
    rollback_svc.record_promotion("sports", "futebol", previous_branch="sports-production")

    for _ in range(10):
        health_svc.record_sample("sports", "futebol", True)

    evaluation = rollback_svc.evaluate("sports", "futebol")
    assert evaluation["decision"] == "hold"


def test_canary_promote_records_rollback_state():
    """auto_promote registra estado para rollback futuro."""
    health_svc = EasUpdateCanaryHealthService()
    for _ in range(10):
        health_svc.record_sample("beauty", "trancista", True)

    with patch.object(EasUpdateCanaryPromoteService, "evaluate") as mock_eval:
        mock_eval.return_value = {
            "decision": "promote",
            "promote_plan": {"to_production_channel": "beauty-production"},
        }
        EasUpdateCanaryPromoteService().auto_promote("beauty", "trancista", force=True)

    state = EasUpdateCanaryRollbackService().get_promotion_state("beauty", "trancista")
    assert state is not None
    assert state["promoted"] is True


def test_canary_rollback_api(client, admin_headers, db):
    """POST rollback com force."""
    EasUpdateCanaryRollbackService(db=db).record_promotion(
        "clinic", "odontologia", previous_branch="clinic-production"
    )
    response = client.post(
        "/v1/mobile/eas/update/canary/clinic/rollback?segment=odontologia&force=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "rollback"


def test_terraform_policy_passes_all():
    """Políticas embarcadas passam para todos ambientes."""
    result = TerraformPolicyService().evaluate_all()
    assert result["all_passed"] is True
    assert len(result["results"]) == 3


def test_terraform_policy_violation():
    """Violação detectada quando bucket suffix incorreto."""
    pipeline = TerraformPipelineService()
    bad_doc = pipeline.tfvars_for_environment("prod")
    bad_doc = {**bad_doc, "bucket_name": "wrong-bucket"}

    with patch.object(pipeline, "tfvars_for_environment", return_value=bad_doc):
        service = TerraformPolicyService(pipeline_service=pipeline)
        result = service.evaluate_embedded("prod")

    assert result["passed"] is False
    assert any(v["rule_id"] == "prod_bucket_suffix" for v in result["violations"])


def test_terraform_policy_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/policy/dev."""
    response = client.get(
        "/v1/mobile/cdn/terraform/policy/dev",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_terraform_policy_all_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/policy/all/evaluate."""
    response = client.get(
        "/v1/mobile/cdn/terraform/policy/all/evaluate",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["all_passed"] is True


def test_terraform_policy_manifest_api(client):
    """GET /v1/mobile/cdn/terraform/policy."""
    response = client.get("/v1/mobile/cdn/terraform/policy")
    assert response.status_code == 200
    assert "embedded_rules" in response.json()
