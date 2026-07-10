"""
PlatformHealthService — GET /v1/platform/health (R1-F2).
"""
from typing import Any, Dict

from app.core.architecture_metrics import ArchitectureMetricsStore, identified_couplings
from app.core.config import settings
from app.core.core_enforcement import resolve_enforcement_mode
from app.core.feature_flags import feature_flags
from app.core.plugin.registry import plugin_registry
from app.modules.platform.application.plugin_registry_document_service import (
    PluginRegistryDocumentService,
)
from app.modules.platform.application.readiness_score_service import ReadinessScoreService


class PlatformHealthService:
    """
    Agrega saúde arquitetural da plataforma para painel admin e auditorias.
    """

    def health_document(self) -> Dict[str, Any]:
        """
        Monta resposta de platform health.

        Returns:
            Dict version, core, legacy, plugins, featureFlags, architecture, enforcement.
        """
        metrics = ArchitectureMetricsStore.get().snapshot()
        registry = PluginRegistryDocumentService().build_registry()
        readiness = ReadinessScoreService().scoreboard()

        plugin_health = {
            p["plugin_id"]: p["status"] for p in registry["plugins"]
        }

        legacy_http = metrics["http"]
        legacy_requests = (
            legacy_http["by_layer"].get("legacy", 0)
            + legacy_http["by_layer"].get("beautyos", 0)
        )

        flags = {
            key: data["enabled"] for key, data in feature_flags.all_flags().items()
        }

        return {
            "version": settings.APP_VERSION,
            "core": "healthy",
            "legacy": {
                "requests": legacy_requests,
                "percentage": legacy_http.get("legacy_percentage", 0.0),
                "enforcement_mode": resolve_enforcement_mode(),
            },
            "plugins": plugin_health,
            "featureFlags": flags,
            "architecture": {
                "adrVersion": 8,
                "rfcPending": 0,
                "readinessAverage": readiness["average"],
                "couplingsCount": len(identified_couplings()),
            },
            "telemetry": {
                "enabled": feature_flags.is_enabled("legacy.telemetry.enabled"),
                "http_total": legacy_http.get("total", 0),
                "events_published": metrics["events"].get("published_total", 0),
            },
        }

    def architecture_metrics_document(self) -> Dict[str, Any]:
        """
        Métricas arquiteturais detalhadas.

        Returns:
            Dict metrics, couplings, test_coverage, readiness.
        """
        return {
            "metrics": ArchitectureMetricsStore.get().snapshot(),
            "couplings": identified_couplings(),
            "test_coverage": ReadinessScoreService().coverage_summary(),
            "readiness": ReadinessScoreService().scoreboard(),
            "plugins_loaded": len(plugin_registry.list_all()),
        }
