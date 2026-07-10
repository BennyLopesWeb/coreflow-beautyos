"""
CloudFrontBehaviorsService — cache behaviors por tenant/plugin (CF-18).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.plugin_cdn_service import PluginCdnService

logger = get_logger("cloudfront_behaviors")

INFRA_DIR = Path(__file__).resolve().parents[4] / "infra" / "cdn"


class CloudFrontBehaviorsService:
    """
    Gera configuração CloudFront com cache behaviors isolados por plugin.

    Cada tenant recebe path pattern ``/{plugin_id}/.well-known/*`` ou
    host alias dedicado (cdn_host) com TTL e compressão configuráveis.
    """

    def __init__(self, infra_dir: Optional[Path] = None):
        """
        Args:
            infra_dir: Diretório de export infra (default backend/infra/cdn).
        """
        self.infra_dir = infra_dir or INFRA_DIR
        self.plugin_cdn = PluginCdnService()

    def behavior_for_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Gera cache behavior CloudFront para um plugin.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict compatível com AWS CloudFront CacheBehavior.
        """
        cfg = self.plugin_cdn.mobile_config(plugin_id)
        cache_ttl = settings.MOBILE_WELL_KNOWN_CACHE_SECONDS
        path_prefix = f"/{plugin_id}/.well-known/*" if settings.MOBILE_CDN_PER_PLUGIN_PATH else "/.well-known/*"

        return {
            "plugin_id": plugin_id,
            "cdn_host": cfg["cdn_host"],
            "PathPattern": path_prefix,
            "TargetOriginId": settings.CDN_CLOUDFRONT_ORIGIN_ID,
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": ["GET", "HEAD", "OPTIONS"],
            "CachedMethods": ["GET", "HEAD"],
            "Compress": True,
            "MinTTL": 0,
            "DefaultTTL": cache_ttl,
            "MaxTTL": cache_ttl,
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
            },
            "ResponseHeadersPolicyId": settings.CDN_CLOUDFRONT_RESPONSE_HEADERS_POLICY_ID,
        }

    def host_aliases(self) -> List[str]:
        """
        Lista CNAMEs CloudFront por plugin + host global.

        Returns:
            Lista de hostnames únicos.
        """
        hosts = {settings.MOBILE_UNIVERSAL_LINK_HOST}
        for manifest in plugin_registry.list_all():
            cfg = self.plugin_cdn.mobile_config(manifest.plugin_id)
            hosts.add(cfg["cdn_host"])
        return sorted(hosts)

    def distribution_config(self) -> Dict[str, Any]:
        """
        Monta configuração CloudFront multi-tenant completa.

        Returns:
            Dict com Origins, CacheBehaviors e Aliases por plugin.
        """
        behaviors = [self.behavior_for_plugin(p.plugin_id) for p in plugin_registry.list_all()]
        global_behavior = {
            "PathPattern": "/.well-known/*",
            "TargetOriginId": settings.CDN_CLOUDFRONT_ORIGIN_ID,
            "ViewerProtocolPolicy": "redirect-to-https",
            "AllowedMethods": ["GET", "HEAD"],
            "CachedMethods": ["GET", "HEAD"],
            "Compress": True,
            "DefaultTTL": settings.MOBILE_WELL_KNOWN_CACHE_SECONDS,
            "MaxTTL": settings.MOBILE_WELL_KNOWN_CACHE_SECONDS,
        }

        return {
            "Comment": f"CoreFlow CDN multi-tenant v{settings.APP_VERSION}",
            "Enabled": True,
            "Aliases": self.host_aliases(),
            "Origins": [
                {
                    "Id": settings.CDN_CLOUDFRONT_ORIGIN_ID,
                    "DomainName": f"{settings.CDN_S3_BUCKET}.s3.{settings.CDN_S3_REGION}.amazonaws.com",
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
            "DefaultCacheBehavior": global_behavior,
            "CacheBehaviors": behaviors,
            "PriceClass": settings.CDN_CLOUDFRONT_PRICE_CLASS,
        }

    def export_to_disk(self) -> Dict[str, str]:
        """
        Exporta ``cloudfront-behaviors.json`` para infra/cdn/.

        Returns:
            Dict com path do arquivo exportado.
        """
        self.infra_dir.mkdir(parents=True, exist_ok=True)
        config = self.distribution_config()
        target = self.infra_dir / "cloudfront-behaviors.json"
        target.write_text(json.dumps(config, indent=2), encoding="utf-8")
        logger.info(f"[cloudfront] Config exportada → {target}")
        return {"cloudfront_behaviors": str(target)}
