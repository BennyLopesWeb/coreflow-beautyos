"""
Middleware Sunset — sinaliza depreciação de rotas legado BeautyOS.

Conforme RFC 8594, adiciona headers ``Sunset``, ``Deprecation`` e ``Link``
apontando para equivalentes CoreFlow v1.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


@dataclass(frozen=True)
class LegacyRouteSunset:
    """
    Configuração de sunset para um prefixo de rota legada.

    Attributes:
        prefix: Prefixo do path (ex.: ``/trancas``).
        successor: Rota CoreFlow v1 sucessora.
        sunset_date: Data HTTP de descontinuação (RFC 8594).
    """

    prefix: str
    successor: str
    sunset_date: str = "Sat, 01 Jan 2028 00:00:00 GMT"


# Rotas legado → sucessoras CoreFlow v1 (Strangler Fig)
LEGACY_SUNSET_ROUTES: tuple[LegacyRouteSunset, ...] = (
    LegacyRouteSunset("/trancas", "/v1/catalogs"),
    LegacyRouteSunset("/agenda/disponibilidade", "/v1/scheduling/availability"),
    LegacyRouteSunset("/agenda/agendamentos", "/v1/bookings"),
    LegacyRouteSunset("/agendamentos", "/v1/bookings"),
    LegacyRouteSunset("/reservations", "/v1/bookings"),
    LegacyRouteSunset("/pagamentos", "/v1/bookings"),
    LegacyRouteSunset("/fila", "/v1/waitlist"),
)


def match_legacy_sunset(path: str) -> Optional[LegacyRouteSunset]:
    """
    Encontra regra de sunset para o path da requisição.

    Rotas mais específicas (path completo) têm prioridade sobre prefixos.

    Args:
        path: Path da URL (ex.: ``/agenda/disponibilidade``).

    Returns:
        LegacyRouteSunset correspondente ou None.
    """
    ordered = sorted(LEGACY_SUNSET_ROUTES, key=lambda r: len(r.prefix), reverse=True)
    for rule in ordered:
        if path == rule.prefix or path.startswith(f"{rule.prefix}/"):
            return rule
    return None


def apply_sunset_headers(response: Response, rule: LegacyRouteSunset) -> None:
    """
    Aplica headers RFC de depreciação na resposta HTTP.

    Args:
        response: Resposta Starlette/FastAPI.
        rule: Regra de sunset matched.

    Returns:
        None
    """
    response.headers["Sunset"] = settings.LEGACY_SUNSET_DATE
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'<{rule.successor}>; rel="successor-version"'


class LegacySunsetMiddleware(BaseHTTPMiddleware):
    """
    Middleware HTTP que marca rotas legado com headers Sunset/Deprecation.

    Args:
        app: Aplicação ASGI.
        enabled: Se False, pass-through sem alterar headers.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processa requisição e injeta headers de sunset quando aplicável.

        Args:
            request: Requisição HTTP.
            call_next: Próximo handler ASGI.

        Returns:
            Response com headers opcionais de depreciação.
        """
        response = await call_next(request)
        if not self.enabled:
            return response

        rule = match_legacy_sunset(request.url.path)
        if rule:
            apply_sunset_headers(response, rule)
        return response
