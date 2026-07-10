"""Testes CF-25 — PagerDuty/Opsgenie, canary DB persist, Terraform Cloud."""
import pytest

from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_rollback_service import EasUpdateCanaryRollbackService
from app.modules.mobile.infrastructure.canary_promotion_repository import CanaryPromotionRepository
from app.modules.mobile.application.terraform_cloud_policy_service import TerraformCloudPolicyService
from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService


@pytest.fixture(autouse=True)
def reset_state(db, monkeypatch):
    """Reseta estado canary; CF-25 usa persistência DB."""
    plugin_registry.load_all()
    EasUpdateCanaryHealthService.reset_samples()
    EasUpdateCanaryRollbackService.reset_state(db=db)
    monkeypatch.setattr(settings, "MOBILE_EAS_UPDATE_CANARY_PERSIST_DB", True)


def test_alertmanager_pagerduty_receiver():
    """Config inclui receiver PagerDuty quando habilitado."""
    cfg = AlertmanagerRulesService().alertmanager_config()
    names = [r["name"] for r in cfg["receivers"]]
    assert "coreflow-pagerduty" in names
    pd = next(r for r in cfg["receivers"] if r["name"] == "coreflow-pagerduty")
    assert "pagerduty_configs" in pd


def test_alertmanager_opsgenie_receiver():
    """Config inclui receiver Opsgenie quando habilitado."""
    cfg = AlertmanagerRulesService().alertmanager_config()
    names = [r["name"] for r in cfg["receivers"]]
    assert "coreflow-opsgenie" in names


def test_alertmanager_manifest_pagerduty_flag():
    """Manifest indica integrações on-call."""
    manifest = AlertmanagerRulesService().manifest()
    assert manifest["pagerduty_enabled"] is True
    assert manifest["opsgenie_enabled"] is True


def test_canary_promotion_persist_db(db):
    """Promoção sobrevive via core_canary_promotions."""
    svc = EasUpdateCanaryRollbackService(db=db)
    svc.record_promotion("beauty", "trancista", previous_branch="beauty-production")

    reloaded = EasUpdateCanaryRollbackService(db=db)
    state = reloaded.get_promotion_state("beauty", "trancista")
    assert state is not None
    assert state["previous_branch"] == "beauty-production"
    assert state.get("id") is not None


def test_canary_promotion_survives_new_service_instance(db):
    """Nova instância de serviço lê promoção do banco."""
    EasUpdateCanaryRollbackService(db=db).record_promotion(
        "sports", "futebol", previous_branch="sports-production"
    )
    active = EasUpdateCanaryRollbackService(db=db).list_active_promotions()
    assert len(active) == 1
    assert active[0]["plugin_id"] == "sports"


def test_canary_rollback_clears_db(db):
    """Rollback marca promoção inativa no banco."""
    health_svc = EasUpdateCanaryHealthService()
    svc = EasUpdateCanaryRollbackService(db=db)
    svc.record_promotion("beauty", "trancista", previous_branch="beauty-production")
    for _ in range(10):
        health_svc.record_sample("beauty", "trancista", False)
    svc.auto_rollback("beauty", "trancista")
    assert svc.get_promotion_state("beauty", "trancista") is None


def test_canary_promotions_api(client, admin_headers, db):
    """GET /v1/mobile/eas/update/canary/promotions."""
    EasUpdateCanaryRollbackService(db=db).record_promotion(
        "clinic", "odontologia", previous_branch="clinic-production"
    )
    response = client.get(
        "/v1/mobile/eas/update/canary/promotions",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_terraform_cloud_policy_set_document():
    """Policy set contém OPA + Sentinel por ambiente."""
    doc = TerraformCloudPolicyService().policy_set_document()
    assert doc["name"] == settings.TERRAFORM_CLOUD_POLICY_SET_NAME
    assert len(doc["policies"]) == 6
    kinds = {p["kind"] for p in doc["policies"]}
    assert kinds == {"opa", "sentinel"}


def test_terraform_cloud_evaluate_all():
    """Validação combinada OPA + Sentinel passa."""
    result = TerraformCloudPolicyService().evaluate_all()
    assert result["all_passed"] is True


def test_terraform_cloud_export(tmp_path):
    """export_policy_set grava policy-set.json."""
    service = TerraformCloudPolicyService(tfc_dir=tmp_path)
    paths = service.export_policy_set()
    assert (tmp_path / "policy-set.json").is_file()
    assert "policy_set" in paths


def test_terraform_cloud_api(client, admin_headers):
    """GET /v1/mobile/cdn/terraform/cloud/policy-set."""
    response = client.get("/v1/mobile/cdn/terraform/cloud/policy-set")
    assert response.status_code == 200
    assert "policies" in response.json()


def test_terraform_cloud_export_api(client, admin_headers, tmp_path, monkeypatch):
    """POST export policy set."""
    monkeypatch.setattr(
        "app.modules.mobile.application.terraform_cloud_policy_service.TFC_DIR",
        tmp_path,
    )
    response = client.post(
        "/v1/mobile/cdn/terraform/cloud/policy-set/export",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "policy_set" in response.json()


def test_canary_repository_memory_fallback():
    """Sem DB usa memória quando persist desabilitado."""
    repo = CanaryPromotionRepository(db=None)
    state = {
        "plugin_id": "beauty",
        "segment": "trancista",
        "previous_branch": "x",
        "promoted_branch": "y",
        "production_channel": "z",
    }
    repo.save_promotion(state)
    assert repo.get_active("beauty", "trancista") is not None
