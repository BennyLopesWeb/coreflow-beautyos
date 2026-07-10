"""
Router API v1 — Mobile utilities (CF-14/15/16).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.identity.api.deps import get_current_admin_user
from app.models.user import User
from app.modules.mobile.application.eas_update_service import EasUpdateService
from app.modules.mobile.application.eas_update_canary_service import EasUpdateCanaryService
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_promote_service import EasUpdateCanaryPromoteService
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
from app.modules.mobile.application.eas_update_canary_rollback_service import EasUpdateCanaryRollbackService
from app.modules.mobile.application.terraform_drift_service import TerraformDriftService
from app.modules.mobile.application.terraform_policy_service import TerraformPolicyService
from app.modules.mobile.application.terraform_sentinel_service import TerraformSentinelService
from app.modules.mobile.application.terraform_cloud_policy_service import TerraformCloudPolicyService
from app.modules.mobile.application.terraform_export_service import TerraformExportService
from app.modules.mobile.application.eas_submit_service import EasSubmitService
from app.modules.mobile.application.cloudfront_behaviors_service import CloudFrontBehaviorsService
from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService
from app.modules.mobile.application.cdn_s3_sync_service import CdnS3SyncService
from app.modules.mobile.application.plugin_cdn_service import PluginCdnService
from app.modules.mobile.application.well_known_export_service import WellKnownExportService
from app.modules.mobile.application.well_known_service import WellKnownService

router = APIRouter(prefix="/v1/mobile", tags=["CoreFlow — Mobile"])


@router.get("/well-known/preview")
def well_known_preview() -> Dict[str, Any]:
    """
    Preview público das configurações Universal/App Links.

    Returns:
        Host, app IDs e URLs dos arquivos .well-known.
    """
    return WellKnownService().preview()


@router.get("/cdn/manifest")
def cdn_manifest(
    plugin_id: Optional[str] = Query(None, description="Filtrar por plugin (beauty, sports, clinic)"),
) -> Dict[str, Any]:
    """
    Manifest CDN multi-tenant por plugin.

    Args:
        plugin_id: Plugin opcional para filtrar.

    Returns:
        URLs, cache headers e configs por plugin.
    """
    return PluginCdnService().cdn_manifest(plugin_id=plugin_id)


@router.get("/cdn/plugins")
def list_plugin_cdn_configs() -> List[Dict[str, Any]]:
    """
    Lista config mobile/CDN de todos os plugins registrados.

    Returns:
        Lista de configs ios/android por plugin.
    """
    service = PluginCdnService()
    from app.core.plugin.registry import plugin_registry

    return [service.mobile_config(p.plugin_id) for p in plugin_registry.list_all()]


@router.post("/well-known/export")
def well_known_export(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta AASA e assetlinks global para ``backend/cdn/.well-known/`` (admin).

    Returns:
        Paths dos arquivos gravados no disco.
    """
    return WellKnownExportService().export_to_disk()


@router.post("/well-known/export-all")
def well_known_export_all(
    _: User = Depends(get_current_admin_user),
) -> List[Dict[str, str]]:
    """
    Exporta .well-known global + por plugin (CF-16 multi-tenant CDN).

    Returns:
        Lista de paths exportados por plugin_id.
    """
    return PluginCdnService().export_all_plugins()


@router.get("/eas/profiles")
def list_eas_profiles(
    profile: Optional[str] = Query(None, description="development | preview | production"),
) -> List[Dict[str, Any]]:
    """
    Lista perfis EAS white-label por plugin (CF-17).

    Args:
        profile: Filtrar por perfil base ou None para todos.

    Returns:
        Perfis com bundle IDs e env vars por plugin.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasWhitelabelService().list_plugin_profiles(profile_name=profile)


@router.get("/eas/profiles/{plugin_id}")
def get_eas_profile(
    plugin_id: str,
    profile: str = Query("preview", description="development | preview | production"),
) -> Dict[str, Any]:
    """
    Obtém perfil EAS white-label de um plugin.

    Args:
        plugin_id: beauty, sports, clinic.
        profile: Perfil base EAS.

    Returns:
        Config completa do perfil white-label.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasWhitelabelService().build_profile(plugin_id, profile)


@router.get("/eas/app-config/{plugin_id}")
def get_eas_app_config_overlay(plugin_id: str) -> Dict[str, Any]:
    """
    Overlay app.json Expo para white-label de um plugin.

    Args:
        plugin_id: ID do plugin vertical.

    Returns:
        Fragmento app.json com name, slug e bundle IDs.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasWhitelabelService().app_config_overlay(plugin_id)


@router.post("/eas/generate")
def generate_eas_plugins_file(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Gera ``frontend/eas.plugins.json`` com perfis white-label (admin).

    Returns:
        Documento eas.plugins.json gravado.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasWhitelabelService().generate_plugins_file()


@router.post("/cdn/sync-s3")
def cdn_sync_s3(
    dry_run: bool = Query(True, description="Simular upload sem gravar no S3"),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Sincroniza CDN local para S3 e invalida CloudFront (CF-17).

    Args:
        dry_run: Se True, apenas lista arquivos sem upload.

    Returns:
        Resumo de uploads e invalidação CloudFront.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return CdnS3SyncService().sync_all(dry_run=dry_run)


@router.get("/eas/submit/profiles")
def list_eas_submit_profiles() -> List[Dict[str, Any]]:
    """
    Lista perfis EAS Submit por plugin (CF-18).

    Returns:
        Perfis submit App Store / Play Store white-label.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasSubmitService().list_submit_profiles()


@router.get("/eas/submit/profiles/{plugin_id}")
def get_eas_submit_profile(plugin_id: str) -> Dict[str, Any]:
    """
    Obtém perfil EAS Submit de um plugin.

    Args:
        plugin_id: beauty, sports, clinic.

    Returns:
        Config submit iOS/Android do plugin.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasSubmitService().build_submit_profile(plugin_id)


@router.post("/eas/submit/generate")
def generate_eas_submit_file(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Gera ``frontend/eas.submit.json`` com perfis submit (admin).

    Returns:
        Documento eas.submit.json gravado.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasSubmitService().generate_submit_file()


@router.get("/cdn/cloudfront-behaviors")
def cloudfront_behaviors(
    plugin_id: Optional[str] = Query(None, description="Filtrar behavior por plugin"),
) -> Dict[str, Any]:
    """
    Configuração CloudFront cache behaviors por tenant (CF-18).

    Args:
        plugin_id: Plugin opcional para filtrar.

    Returns:
        Distribution config com behaviors multi-tenant.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    service = CloudFrontBehaviorsService()
    if plugin_id:
        return {"behavior": service.behavior_for_plugin(plugin_id)}
    return service.distribution_config()


@router.post("/cdn/cloudfront-behaviors/export")
def export_cloudfront_behaviors(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta cloudfront-behaviors.json para infra/cdn/ (admin).

    Returns:
        Path do arquivo exportado.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return CloudFrontBehaviorsService().export_to_disk()


@router.get("/eas/update/channels")
def list_eas_update_channels() -> List[Dict[str, Any]]:
    """
    Lista canais EAS Update (OTA) por plugin (CF-19).

    Returns:
        Perfis preview/production com channel e branch.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateService().list_update_profiles()


@router.get("/eas/update/channels/{plugin_id}")
def get_eas_update_channel(
    plugin_id: str,
    environment: str = Query("preview", description="preview | production"),
) -> Dict[str, Any]:
    """
    Obtém canal EAS Update de um plugin.

    Args:
        plugin_id: beauty, sports, clinic.
        environment: preview | production.

    Returns:
        Config OTA com channel, branch e runtime_version.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateService().build_update_profile(plugin_id, environment)


@router.post("/eas/update/generate")
def generate_eas_update_file(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Gera ``frontend/eas.update.json`` com canais OTA (admin).

    Returns:
        Documento eas.update.json gravado.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateService().generate_update_file()


@router.get("/eas/update/rollout/{plugin_id}")
def get_eas_update_rollout_plan(
    plugin_id: str,
    target_percentage: Optional[int] = Query(None, ge=1, le=100),
) -> Dict[str, Any]:
    """
    Plano de rollout gradual OTA para um plugin (CF-20).

    Args:
        plugin_id: beauty, sports, clinic.
        target_percentage: Percentual alvo ou None para config do manifest.

    Returns:
        Stages aplicáveis e comandos eas update sugeridos.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateService().build_rollout_plan(plugin_id, target_percentage)


@router.get("/eas/update/canary/promotions")
def list_canary_promotions(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> List[Dict[str, Any]]:
    """
    Lista promoções canary ativas persistidas (CF-25).

    Returns:
        Lista de estados de promoção no banco.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateCanaryRollbackService(db=db).list_active_promotions()


@router.get("/eas/update/canary/{plugin_id}")
def get_eas_update_canary_plan(
    plugin_id: str,
    segment: str = Query(..., description="Segmento do manifest (ex.: trancista)"),
    percentage: Optional[int] = Query(None, ge=1, le=100),
) -> Dict[str, Any]:
    """
    Plano canary OTA por segmento de usuário (CF-21).

    Args:
        plugin_id: beauty, sports, clinic.
        segment: Segmento de mercado do manifest.
        percentage: Percentual canary ou default do manifest.

    Returns:
        Channel, branch, env vars e comando eas update.

    Raises:
        HTTPException 400: Segmento inválido.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryService().build_canary_plan(plugin_id, segment, percentage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eas/update/canary/{plugin_id}/segments")
def list_eas_canary_segments(plugin_id: str) -> List[str]:
    """
    Lista segmentos canary disponíveis para um plugin.

    Args:
        plugin_id: ID do plugin vertical.

    Returns:
        Lista de segment ids.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateCanaryService().list_segments(plugin_id)


@router.get("/eas/update/canary/{plugin_id}/health")
def get_eas_canary_health(
    plugin_id: str,
    segment: str = Query(..., description="Segmento canary"),
) -> Dict[str, Any]:
    """
    Health check do canary OTA por segmento (CF-22).

    Args:
        plugin_id: beauty, sports, clinic.
        segment: Segmento alvo.

    Returns:
        healthy, success_rate, samples e thresholds.

    Raises:
        HTTPException 400: Segmento inválido.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryHealthService().probe_health(plugin_id, segment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eas/update/canary/{plugin_id}/health/sample")
def record_eas_canary_health_sample(
    plugin_id: str,
    segment: str = Query(...),
    success: bool = Query(True),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Registra amostra de health canary (modo mock, CF-22).

    Args:
        plugin_id: ID do plugin.
        segment: Segmento canary.
        success: True se sessão/requisição OK.

    Returns:
        Estatísticas atualizadas após ingestão.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    service = EasUpdateCanaryHealthService()
    stats = service.record_sample(plugin_id, segment, success)
    health = service.probe_health(plugin_id, segment)
    return {"sample_recorded": success, "stats": stats, "health": health}


@router.get("/eas/update/canary/{plugin_id}/promote/evaluate")
def evaluate_eas_canary_promote(
    plugin_id: str,
    segment: str = Query(..., description="Segmento canary"),
) -> Dict[str, Any]:
    """
    Avalia se canary está pronto para auto-promote (CF-22).

    Args:
        plugin_id: ID do plugin vertical.
        segment: Segmento canary.

    Returns:
        decision promote|hold com health e motivo.

    Raises:
        HTTPException 400: Segmento inválido.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryPromoteService().evaluate(plugin_id, segment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eas/update/canary/{plugin_id}/promote")
def promote_eas_canary(
    plugin_id: str,
    segment: str = Query(...),
    force: bool = Query(False, description="Ignorar health check"),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Auto-promote canary → production quando health OK (CF-22).

    Args:
        plugin_id: ID do plugin.
        segment: Segmento canary.
        force: Promover mesmo com health reprovado.

    Returns:
        Plano de promoção EAS channel production.

    Raises:
        HTTPException 400: Health reprovado ou segmento inválido.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryPromoteService().auto_promote(plugin_id, segment, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eas/update/canary/{plugin_id}/rollback/evaluate")
def evaluate_eas_canary_rollback(
    plugin_id: str,
    segment: str = Query(..., description="Segmento canary"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Avalia se rollback automático é necessário (CF-23).

    Args:
        plugin_id: ID do plugin vertical.
        segment: Segmento canary promovido.

    Returns:
        decision rollback|hold|noop com health e motivo.

    Raises:
        HTTPException 400: Segmento inválido.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryRollbackService(db=db).evaluate(plugin_id, segment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eas/update/canary/{plugin_id}/rollback")
def rollback_eas_canary(
    plugin_id: str,
    segment: str = Query(...),
    force: bool = Query(False, description="Forçar rollback"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Executa rollback canary → branch production anterior (CF-23).

    Args:
        plugin_id: ID do plugin.
        segment: Segmento canary.
        force: Ignorar health degradation check.

    Returns:
        Plano de rollback EAS channel:edit.

    Raises:
        HTTPException 400: Rollback não elegível.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    try:
        return EasUpdateCanaryRollbackService(db=db).auto_rollback(plugin_id, segment, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eas/update/canary/rollback/scan")
def scan_eas_canary_rollback(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Scan de promoções canary ativas e rollback automático (CF-24/25).

    Returns:
        Resumo scanned, counts rollback/hold/noop e results.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return EasUpdateCanaryRollbackService(db=db).scan_and_rollback()


@router.post("/cdn/terraform/pipeline/export")
def export_terraform_pipeline(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Exporta todos ambientes + pipeline.json (CF-21).

    Returns:
        Manifest de pipeline e paths exportados por ambiente.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    service = TerraformPipelineService()
    environments = service.export_all_environments()
    manifest = service.export_pipeline_manifest()
    return {"environments": environments, **manifest}


@router.get("/cdn/terraform/pipeline")
def get_terraform_pipeline_manifest() -> Dict[str, Any]:
    """
    Preview do pipeline dev → staging → prod (CF-21).

    Returns:
        Ordem de promoção e gates de aprovação.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return TerraformPipelineService().pipeline_manifest()


@router.post("/cdn/terraform/export")
def export_terraform_cdn(
    environment: str = Query("dev", description="Ambiente Terraform"),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta terraform.tfvars.json para infra/terraform (CF-19/20).

    Args:
        environment: dev | staging | prod.

    Returns:
        Paths dos arquivos exportados.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    service = TerraformExportService()
    return service.export_tfvars(environment)


@router.get("/cdn/terraform/backend")
def get_terraform_backend_config(
    environment: str = Query("dev", description="Ambiente Terraform"),
) -> Dict[str, Any]:
    """
    Preview da configuração de remote state S3 (CF-20).

    Args:
        environment: dev | staging | prod.

    Returns:
        Dict bucket/key/region/dynamodb_table.
    """
    return TerraformExportService().backend_config(environment)


@router.get("/cdn/terraform/drift")
def get_terraform_drift(
    environment: str = Query("dev", description="Ambiente Terraform"),
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Relatório de drift config/plan para um ambiente (CF-22).

    Args:
        environment: dev | staging | prod.

    Returns:
        Dict has_drift, config hash diff e plan opcional.

    Raises:
        HTTPException 400: Drift desabilitado ou ambiente inválido.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_DRIFT_ENABLED:
        raise HTTPException(status_code=400, detail="Drift detection desabilitado")

    plugin_registry.load_all()
    try:
        return TerraformDriftService().drift_report(environment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cdn/terraform/drift/all")
def get_terraform_drift_all(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Drift de config em todos ambientes do pipeline (CF-22).

    Returns:
        Dict has_any_drift e lista por ambiente.
    """
    from app.core.config import settings as app_settings
    from app.core.plugin.registry import plugin_registry

    if not app_settings.TERRAFORM_DRIFT_ENABLED:
        raise HTTPException(status_code=400, detail="Drift detection desabilitado")

    plugin_registry.load_all()
    return TerraformDriftService().detect_all_config_drift()


@router.get("/cdn/terraform/policy")
def get_terraform_policy_manifest() -> Dict[str, Any]:
    """
    Manifest das políticas OPA Terraform (CF-23).

    Returns:
        Regras embarcadas, paths e engine configurado.
    """
    return TerraformPolicyService().policy_manifest()


@router.get("/cdn/terraform/policy/{environment}")
def evaluate_terraform_policy(
    environment: str,
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Avalia tfvars contra políticas OPA/Sentinel (CF-23).

    Args:
        environment: dev | staging | prod.

    Returns:
        passed, violations e engine usado.

    Raises:
        HTTPException 400: Policy desabilitado ou ambiente inválido.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_OPA_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform OPA desabilitado")

    plugin_registry.load_all()
    try:
        return TerraformPolicyService().evaluate(environment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cdn/terraform/policy/all/evaluate")
def evaluate_terraform_policy_all(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Avalia políticas em todos ambientes do pipeline (CF-23).

    Returns:
        all_passed e resultados por ambiente.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_OPA_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform OPA desabilitado")

    plugin_registry.load_all()
    return TerraformPolicyService().evaluate_all()


@router.get("/cdn/terraform/sentinel")
def get_terraform_sentinel_manifest() -> Dict[str, Any]:
    """
    Manifest políticas Sentinel enterprise (CF-24).

    Returns:
        Regras, tags obrigatórias e paths sentinel/.
    """
    return TerraformSentinelService().policy_manifest()


@router.get("/cdn/terraform/sentinel/{environment}")
def evaluate_terraform_sentinel(
    environment: str,
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Avalia políticas Sentinel enterprise por ambiente (CF-24).

    Args:
        environment: dev | staging | prod.

    Returns:
        passed, violations e policy_level=enterprise.

    Raises:
        HTTPException 400: Sentinel desabilitado ou ambiente inválido.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_SENTINEL_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform Sentinel desabilitado")

    plugin_registry.load_all()
    try:
        return TerraformSentinelService().evaluate(environment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cdn/terraform/sentinel/all/evaluate")
def evaluate_terraform_sentinel_all(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Avalia Sentinel enterprise em todos ambientes (CF-24).

    Returns:
        all_passed e results por ambiente.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_SENTINEL_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform Sentinel desabilitado")

    plugin_registry.load_all()
    return TerraformSentinelService().evaluate_all()


@router.get("/cdn/terraform/cloud/policy-set")
def get_terraform_cloud_policy_set() -> Dict[str, Any]:
    """
    Preview policy set Terraform Cloud OPA + Sentinel (CF-25).

    Returns:
        Document policy set + validação local.
    """
    from app.core.plugin.registry import plugin_registry

    plugin_registry.load_all()
    return TerraformCloudPolicyService().sync_manifest()


@router.post("/cdn/terraform/cloud/policy-set/export")
def export_terraform_cloud_policy_set(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Exporta policy-set.json para infra/terraform/cloud/ (CF-25).

    Returns:
        Path do arquivo exportado.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_CLOUD_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform Cloud desabilitado")

    plugin_registry.load_all()
    return TerraformCloudPolicyService().export_policy_set()


@router.get("/cdn/terraform/cloud/evaluate")
def evaluate_terraform_cloud_policies(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Avalia OPA + Sentinel para todos ambientes (pre-flight TFC).

    Returns:
        all_passed e results combinados por ambiente.
    """
    from app.core.plugin.registry import plugin_registry

    if not settings.TERRAFORM_CLOUD_ENABLED:
        raise HTTPException(status_code=400, detail="Terraform Cloud desabilitado")

    plugin_registry.load_all()
    return TerraformCloudPolicyService().evaluate_all()
