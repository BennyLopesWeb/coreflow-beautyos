"""
LegacyTelemetryMiddleware — métricas HTTP por camada API (R1-F1 / RFC-002).

Registra utilização, latência e erros antes de sunset legado.
"""
import time
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.feature_flags import feature_flags
from app.core.legacy_route_map import classify_api_layer, find_core_successor


class LegacyTelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware Prometheus para requisições HTTP por layer (legacy/beautyos/core).

    Ativo quando ``PROMETHEUS_ENABLED`` e ``FEATURE_LEGACY_TELEMETRY_ENABLED``.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Registra métricas e headers de successor opcional.

        Args:
            request: Requisição HTTP.
            call_next: Próximo handler.

        Returns:
            Response com header X-CoreFlow-Layer quando telemetria ativa.
        """
        if not settings.PROMETHEUS_ENABLED or not feature_flags.is_enabled(
            "legacy.telemetry.enabled"
        ):
            return await call_next(request)

        layer = classify_api_layer(request.url.path)
        method = request.method.upper()
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-CoreFlow-Layer"] = layer
            successor = find_core_successor(method, request.url.path)
            if successor and layer in ("legacy", "beautyos"):
                response.headers["X-CoreFlow-Successor"] = successor
            return response
        finally:
            duration = time.perf_counter() - start
            from app.core.prometheus_metrics import record_http_request

            record_http_request(
                layer=layer,
                method=method,
                status_class=_status_class(status_code),
                duration_seconds=duration,
            )
            try:
                from app.core.architecture_metrics import ArchitectureMetricsStore

                ArchitectureMetricsStore.get().record_http(
                    layer=layer,
                    duration_seconds=duration,
                    is_error=status_code >= 400,
                )
            except Exception:
                pass


def _status_class(status_code: int) -> str:
    """
    Agrupa status HTTP em classe (2xx, 4xx, 5xx).

    Args:
        status_code: Código HTTP.

    Returns:
        String classe ou 'unknown'.
    """
    if 200 <= status_code < 300:
        return "2xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"
