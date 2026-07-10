"""
Router .well-known — Universal Links iOS/Android (CF-14/15).

Deve ser montado na raiz da aplicação (sem prefix).
Respostas incluem headers CDN quando ``MOBILE_CDN_ENABLED=true``.
"""
import json

from fastapi import APIRouter, Response

from app.core.config import settings
from app.modules.mobile.application.well_known_service import WellKnownService

router = APIRouter(tags=["Mobile — Well Known"])


def _cdn_headers() -> dict:
    """
    Headers recomendados para cache CDN de arquivos .well-known.

    Returns:
        Dict de headers HTTP (Cache-Control, etc.).
    """
    if not settings.MOBILE_CDN_ENABLED:
        return {}
    max_age = settings.MOBILE_WELL_KNOWN_CACHE_SECONDS
    return {
        "Cache-Control": f"public, max-age={max_age}, s-maxage={max_age}",
        "CDN-Cache-Control": f"max-age={max_age}",
        "Vary": "Accept-Encoding",
    }


@router.get("/.well-known/apple-app-site-association")
def apple_app_site_association():
    """
    Retorna AASA para verificação de Universal Links iOS.

    Content-Type: application/json (requisito Apple).

    Returns:
        JSON apple-app-site-association com headers CDN opcionais.
    """
    body = WellKnownService().apple_app_site_association()
    return Response(
        content=json.dumps(body),
        media_type="application/json",
        headers=_cdn_headers(),
    )


@router.get("/.well-known/assetlinks.json")
def android_asset_links():
    """
    Retorna assetlinks.json para Android App Links.

    Returns:
        JSON array de relações android_app com headers CDN opcionais.
    """
    body = WellKnownService().android_asset_links()
    return Response(
        content=json.dumps(body),
        media_type="application/json",
        headers=_cdn_headers(),
    )
