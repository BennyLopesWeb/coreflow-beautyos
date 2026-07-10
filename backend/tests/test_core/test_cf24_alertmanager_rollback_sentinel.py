"""Testes CF-24 — Alertmanager rules, canary rollback worker, Terraform Sentinel."""
from unittest.mock import patch

import pytest
import yaml

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_rollback_service import EasUpdateCanaryRollbackService
from app.modules.mobile.application.terraform_sentinel_service import TerraformSentinelService
from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService


@pytest.fixture(autouse=True)
def reset_state(db, monkeypatch):
    """Reseta estado canary entre testes CF-24 (in-memory)."""
    monkeypatch.setattr(settings, "MOBILE_EAS_UPDATE_CANARY_PERSIST_DB", False)
    plugin_registry.load_all()
    EasUpdateCanaryHealthService.reset_samples()
    EasUpdateCanaryRollbackService.reset_state(db=db)


def test_alertmanager_prometheus_rules():
    """Rules Prometheus contêm alertas DLQ esperados."""
    rules = AlertmanagerRulesService().prometheus_alert_rules()
    names = [r["alert"] for r in rules["groups"][0]["rules"]]
    assert "CoreFlowDLQPendingHigh" in names
    assert "CoreFlowDLQReplayStalled" in names


def test_alertmanager_config_receivers():
    """Config Alertmanager define rotas critical e dlq."""
    cfg = AlertmanagerRulesService().alertmanager_config()
    receivers = [r["name"] for r in cfg["receivers"]]
    assert "coreflow-critical" in receivers
    assert "coreflow-dlq" in receivers


def test_alertmanager_export_all(tmp_path):
    """export_all grava rules YAML e alertmanager.yml."""
    service = AlertmanagerRulesService(
        alertmanager_dir=tmp_path / "alertmanager",
        prometheus_rules_dir=tmp_path / "prometheus" / "rules",
    )
    paths = service.export_all()
    rules_file = tmp_path / "prometheus" / "rules" / "coreflow-dlq.yml"
    assert rules_file.is_file()
    parsed = yaml.safe_load(rules_file.read_text())
    assert parsed["groups"][0]["name"] == "coreflow_dlq"
    assert "prometheus_rules" in paths


def test_alertmanager_api(client):
    """GET /v1/events/alertmanager/dlq."""
    response = client.get("/v1/events/alertmanager/dlq")
    assert response.status_code == 200
    assert response.json()["rules_count"] >= 4


def test_alertmanager_export_api(client, admin_headers, tmp_path, monkeypatch):
    """POST export alertmanager rules."""
    monkeypatch.setattr(
        "app.modules.observability.application.alertmanager_rules_service.ALERTMANAGER_DIR",
        tmp_path / "am",
    )
    monkeypatch.setattr(
        "app.modules.observability.application.alertmanager_rules_service.PROMETHEUS_RULES_DIR",
        tmp_path / "rules",
    )
    response = client.post(
        "/v1/events/alertmanager/dlq/export",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "prometheus_rules" in response.json()


def test_canary_rollback_scan_triggers_rollback():
    """scan_and_rollback executa rollback em health degradado."""
    health_svc = EasUpdateCanaryHealthService()
    rollback_svc = EasUpdateCanaryRollbackService()
    rollback_svc.record_promotion("beauty", "trancista", previous_branch="beauty-production")

    for _ in range(10):
        health_svc.record_sample("beauty", "trancista", False)

    result = rollback_svc.scan_and_rollback()
    assert result["counts"]["rollback"] == 1
    assert rollback_svc.get_promotion_state("beauty", "trancista") is None


def test_canary_rollback_scan_hold():
    """scan mantém hold quando health OK."""
    health_svc = EasUpdateCanaryHealthService()
    rollback_svc = EasUpdateCanaryRollbackService()
    rollback_svc.record_promotion("sports", "futebol", previous_branch="sports-production")

    for _ in range(10):
        health_svc.record_sample("sports", "futebol", True)

    result = rollback_svc.scan_and_rollback()
    assert result["counts"]["hold"] == 1
    assert result["counts"]["rollback"] == 0


def test_canary_rollback_worker_once():
    """Worker once retorna summary."""
    from app.workers.canary_rollback_worker import run_once

    result = run_once()
    assert "scanned" in result


def test_canary_rollback_scan_api(client, admin_headers):
    """POST /v1/mobile/eas/update/canary/rollback/scan."""
    EasUpdateCanaryRollbackService().record_promotion(
        "clinic", "odontologia", previous_branch="clinic-production"
    )
    EasUpdateCanaryHealthService().record_sample("clinic", "odontologia", False)
    EasUpdateCanaryHealthService().record_sample("clinic", "odontologia", False)
    EasUpdateCanaryHealthService().record_sample("clinic", "odontologia", False)
    EasUpdateCanaryHealthService().record_sample("clinic", "odontologia", False)
    EasUpdateCanaryHealthService().record_sample("clinic", "odontologia", False)

    response = client.post(
        "/v1/mobile/eas/update/canary/rollback/scan",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "counts" in response.json()


def test_terraform_sentinel_passes_all():
    """Sentinel enterprise passa para todos ambientes."""
    result = TerraformSentinelService().evaluate_all()
    assert result["all_passed"] is True
    assert result["policy_level"] == "enterprise"


def test_terraform_sentinel_violation_missing_tag():
    """Violação quando tag CostCenter ausente em prod."""
    service = TerraformSentinelService()
    document = service.pipeline.tfvars_for_environment("prod")
    document["tags"] = {"Environment": "prod", "Component": "CDN", "Version": "1.0"}

    violations = service._check_required_tags(document, "prod")
    assert any(v["rule_id"] == "sentinel_required_tag" for v in violations)


def test_terraform_sentinel_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/sentinel/prod."""
    response = client.get(
        "/v1/mobile/cdn/terraform/sentinel/prod",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_terraform_sentinel_all_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/sentinel/all/evaluate."""
    response = client.get(
        "/v1/mobile/cdn/terraform/sentinel/all/evaluate",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["all_passed"] is True


def test_terraform_sentinel_manifest_api(client):
    """GET /v1/mobile/cdn/terraform/sentinel."""
    response = client.get("/v1/mobile/cdn/terraform/sentinel")
    assert response.status_code == 200
    assert "required_prod_tags" in response.json()
