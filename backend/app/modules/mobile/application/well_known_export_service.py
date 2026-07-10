"""
WellKnownExportService — exporta .well-known para CDN estática (CF-15).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.well_known_service import WellKnownService

logger = get_logger("well_known_export")

CDN_DIR = Path(__file__).resolve().parents[4] / "cdn"


class WellKnownExportService:
    """
    Exporta arquivos AASA e assetlinks para diretório CDN local.

    Em produção, sincronizar ``backend/cdn/.well-known/`` para S3/CloudFront
    ou servir via nginx (``infra/nginx/well-known.conf``).
    """

    def __init__(self, cdn_dir: Optional[Path] = None):
        """
        Args:
            cdn_dir: Raiz do CDN (default backend/cdn).
        """
        self.cdn_dir = cdn_dir or CDN_DIR
        self.well_known = WellKnownService()

    def export_to_disk(self) -> Dict[str, str]:
        """
        Grava apple-app-site-association e assetlinks.json no disco.

        Returns:
            Dict com paths absolutos dos arquivos exportados.
        """
        target = self.cdn_dir / ".well-known"
        target.mkdir(parents=True, exist_ok=True)

        aasa_path = target / "apple-app-site-association"
        asset_path = target / "assetlinks.json"

        aasa_body = self.well_known.apple_app_site_association()
        asset_body = self.well_known.android_asset_links()

        aasa_path.write_text(
            json.dumps(aasa_body, indent=2),
            encoding="utf-8",
        )
        asset_path.write_text(
            json.dumps(asset_body, indent=2),
            encoding="utf-8",
        )

        logger.info(f"[cdn] Well-known exportado → {target}")
        return {
            "apple_app_site_association": str(aasa_path),
            "assetlinks": str(asset_path),
        }

    def cdn_manifest(self) -> Dict[str, Any]:
        """
        Retorna manifest de URLs CDN para deploy e verificação.

        Returns:
            Dict com base URL, arquivos e headers recomendados.
        """
        host = settings.MOBILE_UNIVERSAL_LINK_HOST
        base = settings.MOBILE_CDN_BASE_URL or f"https://{host}"
        cache = settings.MOBILE_WELL_KNOWN_CACHE_SECONDS
        preview = self.well_known.preview()

        files: List[Dict[str, Any]] = [
            {
                "path": "/.well-known/apple-app-site-association",
                "content_type": "application/json",
                "cache_control": f"public, max-age={cache}",
            },
            {
                "path": "/.well-known/assetlinks.json",
                "content_type": "application/json",
                "cache_control": f"public, max-age={cache}",
            },
        ]

        return {
            "cdn_enabled": settings.MOBILE_CDN_ENABLED,
            "cdn_base_url": base.rstrip("/"),
            "universal_link_host": host,
            "cache_seconds": cache,
            "files": [
                {
                    **item,
                    "url": f"{base.rstrip('/')}{item['path']}",
                }
                for item in files
            ],
            "local_export_dir": str(self.cdn_dir / ".well-known"),
            "ios_app_id": preview["ios_app_id"],
            "android_package": preview["android_package"],
            "deploy_hint": "Sync backend/cdn/.well-known/ → CDN ou use make export-well-known",
        }
