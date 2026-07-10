"""
PluginCdnService — CDN .well-known multi-tenant por plugin (CF-16).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.well_known_service import WellKnownService

logger = get_logger("plugin_cdn")

CDN_DIR = Path(__file__).resolve().parents[3] / "cdn"


class PluginCdnService:
    """
    Gera e exporta arquivos .well-known por plugin vertical.

    Cada plugin pode declarar ``mobile:`` no manifest com ios_app_id,
    android_package e fingerprints próprios.
    """

    def __init__(self, cdn_dir: Optional[Path] = None):
        """
        Args:
            cdn_dir: Raiz do CDN (default backend/cdn).
        """
        self.cdn_dir = cdn_dir or CDN_DIR
        self.well_known = WellKnownService()

    def mobile_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve config mobile de um plugin (manifest ou defaults globais).

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict com ios_app_id, android_package, fingerprints, cdn_host.
        """
        manifest = plugin_registry.get(plugin_id)
        if not manifest:
            return self._default_mobile(plugin_id)

        mobile = manifest.mobile or manifest.sdk.get("mobile", {})
        deep_links = manifest.sdk.get("deep_links", {})
        fingerprints = mobile.get("android_fingerprints") or mobile.get(
            "android_sha256_fingerprints"
        )
        if isinstance(fingerprints, list):
            fp_str = ",".join(fingerprints)
        else:
            fp_str = fingerprints or settings.MOBILE_ANDROID_SHA256_FINGERPRINTS

        return {
            "plugin_id": plugin_id,
            "product_name": manifest.product_name or manifest.name,
            "ios_app_id": mobile.get("ios_app_id", settings.MOBILE_IOS_APP_ID),
            "android_package": mobile.get("android_package", settings.MOBILE_ANDROID_PACKAGE),
            "android_fingerprints": fp_str,
            "cdn_host": mobile.get("cdn_host") or deep_links.get("universal_host")
            or settings.MOBILE_UNIVERSAL_LINK_HOST,
            "path_prefix": mobile.get("path_prefix", settings.MOBILE_UNIVERSAL_LINK_PATH_PREFIX),
        }

    def apple_app_site_association(self, plugin_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera AASA para um plugin ou agregado (todos os plugins).

        Args:
            plugin_id: Plugin específico ou None para merge multi-plugin.

        Returns:
            JSON AASA.
        """
        if plugin_id:
            cfg = self.mobile_config(plugin_id)
            prefix = cfg["path_prefix"]
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"
            return {
                "applinks": {
                    "apps": [],
                    "details": [{"appID": cfg["ios_app_id"], "paths": [prefix]}],
                }
            }

        details = []
        for manifest in plugin_registry.list_all():
            cfg = self.mobile_config(manifest.plugin_id)
            prefix = cfg["path_prefix"]
            if not prefix.startswith("/"):
                prefix = f"/{prefix}"
            details.append({"appID": cfg["ios_app_id"], "paths": [prefix]})

        return {"applinks": {"apps": [], "details": details}}

    def android_asset_links(self, plugin_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gera assetlinks para um plugin ou todos.

        Args:
            plugin_id: Plugin específico ou None para lista agregada.

        Returns:
            Lista assetlinks JSON.
        """
        if plugin_id:
            cfg = self.mobile_config(plugin_id)
            fps = [f.strip() for f in cfg["android_fingerprints"].split(",") if f.strip()]
            return [
                {
                    "relation": ["delegate_permission/common.handle_all_urls"],
                    "target": {
                        "namespace": "android_app",
                        "package_name": cfg["android_package"],
                        "sha256_cert_fingerprints": fps,
                    },
                }
            ]

        entries: List[Dict[str, Any]] = []
        seen = set()
        for manifest in plugin_registry.list_all():
            cfg = self.mobile_config(manifest.plugin_id)
            key = (cfg["android_package"], cfg["android_fingerprints"])
            if key in seen:
                continue
            seen.add(key)
            fps = [f.strip() for f in cfg["android_fingerprints"].split(",") if f.strip()]
            entries.append(
                {
                    "relation": ["delegate_permission/common.handle_all_urls"],
                    "target": {
                        "namespace": "android_app",
                        "package_name": cfg["android_package"],
                        "sha256_cert_fingerprints": fps,
                    },
                }
            )
        return entries

    def export_plugin(self, plugin_id: str) -> Dict[str, str]:
        """
        Exporta .well-known de um plugin para ``cdn/{plugin_id}/.well-known/``.

        Args:
            plugin_id: ID do plugin.

        Returns:
            Paths dos arquivos exportados.
        """
        target = self.cdn_dir / plugin_id / ".well-known"
        target.mkdir(parents=True, exist_ok=True)

        aasa_path = target / "apple-app-site-association"
        asset_path = target / "assetlinks.json"

        aasa_path.write_text(
            json.dumps(self.apple_app_site_association(plugin_id), indent=2),
            encoding="utf-8",
        )
        asset_path.write_text(
            json.dumps(self.android_asset_links(plugin_id), indent=2),
            encoding="utf-8",
        )
        logger.info(f"[cdn] Plugin {plugin_id} exportado → {target}")
        return {
            "plugin_id": plugin_id,
            "apple_app_site_association": str(aasa_path),
            "assetlinks": str(asset_path),
        }

    def export_all_plugins(self) -> List[Dict[str, str]]:
        """
        Exporta .well-known para todos os plugins + agregado global.

        Returns:
            Lista de dicts com paths por plugin.
        """
        results = []
        # Global agregado (compat CF-15)
        global_dir = self.cdn_dir / ".well-known"
        global_dir.mkdir(parents=True, exist_ok=True)
        (global_dir / "apple-app-site-association").write_text(
            json.dumps(self.apple_app_site_association(), indent=2),
            encoding="utf-8",
        )
        (global_dir / "assetlinks.json").write_text(
            json.dumps(self.android_asset_links(), indent=2),
            encoding="utf-8",
        )
        results.append(
            {
                "plugin_id": "_global",
                "apple_app_site_association": str(global_dir / "apple-app-site-association"),
                "assetlinks": str(global_dir / "assetlinks.json"),
            }
        )
        for manifest in plugin_registry.list_all():
            results.append(self.export_plugin(manifest.plugin_id))
        return results

    def cdn_manifest(self, plugin_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Manifest CDN multi-tenant com URLs por plugin.

        Args:
            plugin_id: Filtrar por plugin ou None para todos.

        Returns:
            Dict com plugins e URLs de deploy.
        """
        base = settings.MOBILE_CDN_BASE_URL or f"https://{settings.MOBILE_UNIVERSAL_LINK_HOST}"
        cache = settings.MOBILE_WELL_KNOWN_CACHE_SECONDS

        plugins = []
        manifests = plugin_registry.list_all()
        if plugin_id:
            manifests = [m for m in manifests if m.plugin_id == plugin_id]

        for manifest in manifests:
            cfg = self.mobile_config(manifest.plugin_id)
            host = cfg["cdn_host"]
            plugin_base = f"https://{host}"
            prefix = f"/{manifest.plugin_id}" if settings.MOBILE_CDN_PER_PLUGIN_PATH else ""
            plugins.append(
                {
                    "plugin_id": manifest.plugin_id,
                    "product_name": cfg["product_name"],
                    "cdn_host": host,
                    "ios_app_id": cfg["ios_app_id"],
                    "android_package": cfg["android_package"],
                    "files": [
                        {
                            "path": f"{prefix}/.well-known/apple-app-site-association",
                            "url": f"{plugin_base}{prefix}/.well-known/apple-app-site-association",
                            "cache_control": f"public, max-age={cache}",
                        },
                        {
                            "path": f"{prefix}/.well-known/assetlinks.json",
                            "url": f"{plugin_base}{prefix}/.well-known/assetlinks.json",
                            "cache_control": f"public, max-age={cache}",
                        },
                    ],
                }
            )

        return {
            "cdn_enabled": settings.MOBILE_CDN_ENABLED,
            "multi_tenant": True,
            "cdn_base_url": base.rstrip("/"),
            "plugins": plugins,
            "local_export_dir": str(self.cdn_dir),
            "deploy_hint": "make export-well-known-all",
        }

    def _default_mobile(self, plugin_id: str) -> Dict[str, Any]:
        """
        Fallback mobile config usando settings globais.

        Args:
            plugin_id: ID do plugin.

        Returns:
            Config mobile default.
        """
        return {
            "plugin_id": plugin_id,
            "product_name": plugin_id,
            "ios_app_id": settings.MOBILE_IOS_APP_ID,
            "android_package": settings.MOBILE_ANDROID_PACKAGE,
            "android_fingerprints": settings.MOBILE_ANDROID_SHA256_FINGERPRINTS,
            "cdn_host": settings.MOBILE_UNIVERSAL_LINK_HOST,
            "path_prefix": settings.MOBILE_UNIVERSAL_LINK_PATH_PREFIX,
        }
