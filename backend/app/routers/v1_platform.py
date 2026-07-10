"""
Router API v1 — Platform governance (R1-F1 / R1-F2).

Health, metrics, feature flags, plugin registry, readiness — sem alterar regras de negócio.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.feature_flags import feature_flags
from app.core.legacy_route_map import route_mapping_document
from app.modules.identity.api.deps import get_current_admin_user
from app.modules.observability.application.grafana_architecture_dashboard_service import (
    GrafanaArchitectureDashboardService,
)
from app.modules.platform.application.platform_health_service import PlatformHealthService
from app.modules.platform.application.plugin_registry_document_service import (
    PluginRegistryDocumentService,
)
from app.modules.platform.application.readiness_score_service import ReadinessScoreService
from app.models.user import User
from app.shared.events.event_catalog import event_catalog_summary

router = APIRouter(prefix="/v1/platform", tags=["CoreFlow — Platform"])


@router.get("/health")
def platform_health() -> Dict[str, Any]:
    """
    Saúde arquitetural da plataforma (R1-F2).

    Returns:
        version, core, legacy, plugins, featureFlags, architecture, telemetry.
    """
    return PlatformHealthService().health_document()


@router.get("/architecture-metrics")
def architecture_metrics() -> Dict[str, Any]:
    """
    Métricas de qualidade arquitetural (R1-F2).

    Returns:
        HTTP por layer, eventos, couplings, test coverage, readiness.
    """
    return PlatformHealthService().architecture_metrics_document()


@router.get("/plugin-registry")
def plugin_registry_document() -> Dict[str, Any]:
    """
    Plugin Registry documentado (R1-F2).

    Returns:
        plugins com status, dependencies, permissions, menus, routes.
    """
    return PluginRegistryDocumentService().build_registry()


@router.get("/readiness-score")
def readiness_score() -> Dict[str, Any]:
    """
    Core Readiness Score — maturidade arquitetural (R1-F2).

    Returns:
        items com score/status e média.
    """
    return ReadinessScoreService().scoreboard()


@router.get("/feature-flags")
def get_feature_flags() -> Dict[str, Any]:
    """
    Lista feature flags de migração (RFC-002).

    Returns:
        Dict flag_key → enabled + setting name.
    """
    return {
        "description": "Feature flags CoreFlow — migração incremental",
        "flags": feature_flags.all_flags(),
    }


@router.get("/legacy-route-map")
def get_legacy_route_map() -> Dict[str, Any]:
    """
    Mapa Legado / BeautyOS → CoreFlow v1.

    Returns:
        Documento JSON com mappings por layer e domain.
    """
    return route_mapping_document()


@router.get("/event-catalog")
def get_event_catalog() -> Dict[str, Any]:
    """
    Catálogo machine-readable de eventos de domínio.

    Returns:
        Resumo + entries com status implemented/planned/partial.
    """
    return event_catalog_summary()


@router.get("/grafana/dashboard/layers")
def grafana_layers_dashboard_document() -> Dict[str, Any]:
    """
    Documento JSON dashboard Grafana API layers.

    Returns:
        Dashboard uid coreflow-api-layers.
    """
    return GrafanaArchitectureDashboardService().layer_dashboard_document()


@router.post("/grafana/dashboard/layers/export")
def export_grafana_layers_dashboard(
    _: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Exporta dashboard layers + provisioning (admin).

    Returns:
        Paths exportados.
    """
    service = GrafanaArchitectureDashboardService()
    if settings.GRAFANA_DASHBOARDS_ENABLED:
        paths = service.export_all()
    else:
        paths = service.export_layer_dashboard()
    return {"exported": paths, "enabled": settings.GRAFANA_DASHBOARDS_ENABLED}
