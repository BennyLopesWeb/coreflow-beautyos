"""
EasWhitelabelService — perfis EAS white-label por plugin (CF-17).

Gera configurações de build Expo/EAS com bundle IDs, slugs e env vars
derivados dos manifests de plugin.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.plugin_cdn_service import PluginCdnService

logger = get_logger("eas_whitelabel")

FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend"
EAS_PLUGINS_FILE = FRONTEND_DIR / "eas.plugins.json"

BASE_PROFILES = ("development", "preview", "production")


class EasWhitelabelService:
    """
    Monta perfis EAS por plugin vertical para white-label mobile.

    Cada plugin declara ``mobile:`` no manifest com ios_bundle_id,
    android_package, eas_project_id, expo_slug e app_name.
    """

    def __init__(self, frontend_dir: Optional[Path] = None):
        """
        Args:
            frontend_dir: Diretório raiz do frontend Expo (default ../frontend).
        """
        self.frontend_dir = frontend_dir or FRONTEND_DIR
        self.cdn_service = PluginCdnService()

    def mobile_eas_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve config EAS/mobile de um plugin.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict com bundle IDs, slug, project_id, cdn_host e deep link scheme.
        """
        manifest = plugin_registry.get(plugin_id)
        mobile_cfg = self.cdn_service.mobile_config(plugin_id)
        mobile = (manifest.mobile if manifest else {}) or {}
        deep_links = manifest.sdk.get("deep_links", {}) if manifest else {}

        ios_bundle = mobile.get("ios_bundle_id") or mobile_cfg["android_package"].replace(
            "android", "ios"
        )
        if "." in mobile_cfg.get("ios_app_id", ""):
            team_bundle = mobile_cfg["ios_app_id"].split(".", 1)
            if len(team_bundle) == 2 and not mobile.get("ios_bundle_id"):
                ios_bundle = team_bundle[1]

        android_package = mobile_cfg["android_package"]
        if mobile.get("ios_bundle_id") and not mobile.get("android_package"):
            android_package = mobile["ios_bundle_id"]

        return {
            "plugin_id": plugin_id,
            "app_name": mobile.get("app_name") or mobile_cfg["product_name"],
            "expo_slug": mobile.get("expo_slug") or f"{plugin_id}os",
            "ios_bundle_id": mobile.get("ios_bundle_id", ios_bundle),
            "android_package": android_package,
            "eas_project_id": mobile.get(
                "eas_project_id", f"coreflow-{plugin_id}-dev"
            ),
            "cdn_host": mobile_cfg["cdn_host"],
            "deep_link_scheme": deep_links.get("scheme", settings.MOBILE_DEEP_LINK_SCHEME),
            "associated_domain": f"applinks:{mobile_cfg['cdn_host']}",
        }

    def build_profile(
        self,
        plugin_id: str,
        profile_name: str = "preview",
    ) -> Dict[str, Any]:
        """
        Monta um perfil EAS completo para um plugin.

        Args:
            plugin_id: ID do plugin vertical.
            profile_name: development | preview | production.

        Returns:
            Fragmento eas.json ``build.{profile_name}`` com env e bundle IDs.
        """
        cfg = self.mobile_eas_config(plugin_id)
        env = {
            "EXPO_PUBLIC_PLUGIN_ID": plugin_id,
            "EXPO_PUBLIC_PUSH_ENABLED": "true",
            "EXPO_PUBLIC_USE_COREFLOW_V1": "true",
            "EXPO_PUBLIC_UNIVERSAL_LINK_HOST": cfg["cdn_host"],
            "EXPO_PUBLIC_DEEP_LINK_SCHEME": cfg["deep_link_scheme"],
        }

        profile: Dict[str, Any] = {
            "extends": profile_name,
            "env": env,
            "ios": {
                "bundleIdentifier": cfg["ios_bundle_id"],
            },
            "android": {
                "package": cfg["android_package"],
            },
        }

        if profile_name == "production":
            profile["channel"] = f"{plugin_id}-production"
        elif profile_name == "preview":
            profile["channel"] = f"{plugin_id}-preview"

        return {
            "plugin_id": plugin_id,
            "profile_name": profile_name,
            "profile_key": f"{plugin_id}-{profile_name}",
            "eas_project_id": cfg["eas_project_id"],
            "app_name": cfg["app_name"],
            "expo_slug": cfg["expo_slug"],
            "associated_domain": cfg["associated_domain"],
            "profile": profile,
        }

    def list_plugin_profiles(
        self,
        profile_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lista perfis EAS white-label de todos os plugins.

        Args:
            profile_name: Filtrar por perfil base ou None para todos.

        Returns:
            Lista de dicts com profile_key e config por plugin.
        """
        results: List[Dict[str, Any]] = []
        profiles = [profile_name] if profile_name else list(BASE_PROFILES)

        for manifest in plugin_registry.list_all():
            for name in profiles:
                results.append(self.build_profile(manifest.plugin_id, name))

        return results

    def generate_plugins_file(self) -> Dict[str, Any]:
        """
        Gera ``frontend/eas.plugins.json`` com perfis white-label.

        Returns:
            Dict gravado no disco com plugins e build profiles.
        """
        plugins: Dict[str, Any] = {}
        build_profiles: Dict[str, Any] = {}

        for manifest in plugin_registry.list_all():
            pid = manifest.plugin_id
            cfg = self.mobile_eas_config(pid)
            plugins[pid] = cfg
            for name in BASE_PROFILES:
                built = self.build_profile(pid, name)
                build_profiles[built["profile_key"]] = built["profile"]

        document = {
            "version": settings.APP_VERSION,
            "whitelabel_enabled": settings.MOBILE_EAS_WHITELABEL_ENABLED,
            "plugins": plugins,
            "build": build_profiles,
            "usage": "./scripts/eas-ci.sh preview all beauty",
        }

        target = self.frontend_dir / "eas.plugins.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2), encoding="utf-8")
        logger.info(f"[eas] eas.plugins.json gerado → {target}")
        return document

    def app_config_overlay(self, plugin_id: str) -> Dict[str, Any]:
        """
        Gera overlay app.json para um plugin (name, slug, bundle IDs).

        Args:
            plugin_id: ID do plugin.

        Returns:
            Dict compatível com app.config.js / app.json merge.
        """
        cfg = self.mobile_eas_config(plugin_id)
        return {
            "expo": {
                "name": cfg["app_name"],
                "slug": cfg["expo_slug"],
                "ios": {
                    "bundleIdentifier": cfg["ios_bundle_id"],
                    "associatedDomains": [cfg["associated_domain"]],
                },
                "android": {
                    "package": cfg["android_package"],
                    "intentFilters": [
                        {
                            "action": "VIEW",
                            "autoVerify": True,
                            "data": [
                                {
                                    "scheme": "https",
                                    "host": cfg["cdn_host"],
                                    "pathPrefix": "/",
                                }
                            ],
                            "category": ["BROWSABLE", "DEFAULT"],
                        }
                    ],
                },
                "scheme": cfg["deep_link_scheme"],
                "extra": {"eas": {"projectId": cfg["eas_project_id"]}},
            }
        }
