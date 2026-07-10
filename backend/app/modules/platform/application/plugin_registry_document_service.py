"""
PluginRegistryDocumentService — registro documentado de plugins (R1-F2).
"""
from typing import Any, Dict, List

from app.core.config import settings
from app.core.feature_flags import feature_flags
from app.core.plugin.registry import plugin_registry


class PluginRegistryDocumentService:
    """
    Monta documento de Plugin Registry para API e auditorias.

    Inclui status, dependencies, permissions, menus e routes declarados no manifest.
    """

    def build_registry(self) -> Dict[str, Any]:
        """
        Constrói registro completo de plugins carregados.

        Returns:
            Dict com engine_enabled, plugins[], total.
        """
        plugin_registry.load_all()
        plugins: List[Dict[str, Any]] = []

        for manifest in plugin_registry.list_all():
            sdk = manifest.sdk or {}
            plugins.append(
                {
                    "plugin_id": manifest.plugin_id,
                    "name": manifest.name,
                    "product_name": manifest.product_name or manifest.name,
                    "version": manifest.version,
                    "status": self._plugin_status(manifest.plugin_id),
                    "dependencies": {
                        "declared": manifest.dependencies,
                        "core_modules": self._core_dependencies(manifest),
                    },
                    "permissions": self._permissions(manifest),
                    "menus": self._menus(manifest),
                    "routes": sdk.get("routes", {}),
                    "deep_links": sdk.get("deep_links", {}),
                    "features": manifest.features,
                    "segments": manifest.segments,
                }
            )

        return {
            "engine_enabled": feature_flags.is_enabled("plugin.engine.enabled"),
            "total": len(plugins),
            "plugins": plugins,
        }

    @staticmethod
    def _plugin_status(plugin_id: str) -> str:
        """
        Resolve status operacional do plugin.

        Args:
            plugin_id: ID do plugin.

        Returns:
            active | registered | disabled.
        """
        if plugin_id == "beauty":
            return "active"
        return "registered"

    @staticmethod
    def _core_dependencies(manifest) -> List[str]:
        """
        Infere dependências core a partir do manifest.

        Args:
            manifest: PluginManifest.

        Returns:
            Lista de módulos core utilizados.
        """
        deps = ["Identity", "Tenant"]
        sdk_routes = (manifest.sdk or {}).get("routes", {})
        route_to_module = {
            "bookings": "Booking",
            "catalogs": "Catalog",
            "payments": "Payment",
            "waitlist": "Waitlist",
            "workflows": "Workflow",
            "ai": "AI",
        }
        for key in sdk_routes:
            if key in route_to_module:
                deps.append(route_to_module[key])
        return sorted(set(deps))

    @staticmethod
    def _permissions(manifest) -> List[str]:
        """
        Lista permissões declaradas ou inferidas.

        Args:
            manifest: PluginManifest.

        Returns:
            Lista de permission strings.
        """
        perms = [f"plugin:{manifest.plugin_id}:read"]
        if manifest.has_feature("deposit_payment"):
            perms.append(f"plugin:{manifest.plugin_id}:payments")
        if manifest.ai_capabilities:
            perms.append(f"plugin:{manifest.plugin_id}:ai")
        return perms

    @staticmethod
    def _menus(manifest) -> List[Dict[str, str]]:
        """
        Extrai menus do bloco UI/sdk do manifest.

        Args:
            manifest: PluginManifest.

        Returns:
            Lista de entradas menu label + route.
        """
        menus: List[Dict[str, str]] = []
        sdk_routes = (manifest.sdk or {}).get("routes", {})
        for concept, path in sdk_routes.items():
            label = manifest.term(concept, concept.title())
            menus.append({"label": label, "route": path, "concept": concept})
        return menus
