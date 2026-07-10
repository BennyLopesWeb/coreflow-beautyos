"""
WellKnownService — gera arquivos .well-known para Universal/App Links (CF-14).
"""
from typing import Any, Dict, List

from app.core.config import settings


class WellKnownService:
    """
    Produz JSON de verificação iOS (AASA) e Android (assetlinks).

    Hospedados em ``/.well-known/`` no host ``MOBILE_UNIVERSAL_LINK_HOST``.
    """

    def apple_app_site_association(self) -> Dict[str, Any]:
        """
        Gera conteúdo do apple-app-site-association (iOS Universal Links).

        Returns:
            Dict serializável como JSON (sem extensão .json no path).
        """
        app_id = settings.MOBILE_IOS_APP_ID
        paths = self._link_paths()
        return {
            "applinks": {
                "apps": [],
                "details": [
                    {
                        "appID": app_id,
                        "paths": paths,
                    }
                ],
            },
            "webcredentials": {
                "apps": [app_id],
            },
        }

    def android_asset_links(self) -> List[Dict[str, Any]]:
        """
        Gera assetlinks.json para Android App Links.

        Returns:
            Lista de relações delegate_permission para o app Android.
        """
        fingerprints = [
            fp.strip()
            for fp in settings.MOBILE_ANDROID_SHA256_FINGERPRINTS.split(",")
            if fp.strip()
        ]
        return [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": settings.MOBILE_ANDROID_PACKAGE,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]

    def preview(self) -> Dict[str, Any]:
        """
        Resumo das configurações well-known para admin/debug.

        Returns:
            Dict com host, app ids e URLs dos endpoints.
        """
        host = settings.MOBILE_UNIVERSAL_LINK_HOST
        return {
            "universal_link_host": host,
            "ios_app_id": settings.MOBILE_IOS_APP_ID,
            "android_package": settings.MOBILE_ANDROID_PACKAGE,
            "endpoints": {
                "apple_app_site_association": f"https://{host}/.well-known/apple-app-site-association",
                "assetlinks": f"https://{host}/.well-known/assetlinks.json",
            },
            "sample_universal_link": f"https://{host}/salao-demo/bookings/1",
        }

    def _link_paths(self) -> List[str]:
        """
        Paths glob patterns aceitos pelo iOS para deep links universais.

        Returns:
            Lista de patterns AASA (ex.: ``/salao-demo/*`` ou ``/*``).
        """
        prefix = (settings.MOBILE_UNIVERSAL_LINK_PATH_PREFIX or "/*").strip()
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        return [prefix]
