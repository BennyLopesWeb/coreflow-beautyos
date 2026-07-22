"""
Legacy Gone — HTTP 410 para rotas legado removidas (R4-F1 / R4-F9 / ADR-033).

Substitui 405/409 por ``410 Gone`` com Link para a API CoreFlow v1.
``/agenda/disponibilidade`` permanece (só Sunset) até migração scheduling UX.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SUNSET_HTTP_DATE = "Sat, 01 Jan 2028 00:00:00 GMT"


@dataclass(frozen=True)
class LegacyGoneRoute:
    """
    Prefixo de rota legado que retorna 410 Gone.

    Attributes:
        prefix: Prefixo do path HTTP.
        successor: Path CoreFlow v1 sucessor.
    """

    prefix: str
    successor: str


# Rotas de booking legado — todos os métodos (RFC-003 M6 / R4-F1)
BOOKING_LEGACY_GONE_ROUTES: Tuple[LegacyGoneRoute, ...] = (
    LegacyGoneRoute("/agenda/agendamentos", "/v1/bookings"),
    LegacyGoneRoute("/agendamentos", "/v1/bookings"),
    LegacyGoneRoute("/reservations", "/v1/bookings"),
)

# Rotas de pagamento legado — R4-F9 / R4-F10 (após DROP agendamentos)
# Prefixo ``/pagamentos/sinal`` cobre ``/sinal`` e ``/sinal/gerar``.
# ``/pagamentos/comprovante`` também depende de agendamento_id legado.
# ``/payments/deposit`` e ``/payments/final`` (router payments.py) → 410 (R4-F10).
PAYMENT_LEGACY_GONE_ROUTES: Tuple[LegacyGoneRoute, ...] = (
    LegacyGoneRoute("/pagamentos/sinal", "/v1/payments"),
    LegacyGoneRoute("/pagamentos/comprovante", "/v1/payments"),
    LegacyGoneRoute("/payments/deposit", "/v1/payments"),
    LegacyGoneRoute("/payments/final", "/v1/payments"),
)

LEGACY_GONE_ROUTES: Tuple[LegacyGoneRoute, ...] = (
    BOOKING_LEGACY_GONE_ROUTES + PAYMENT_LEGACY_GONE_ROUTES
)


def match_booking_legacy_gone(path: str) -> Optional[LegacyGoneRoute]:
    """
    Encontra regra 410 para path de booking legado (compat R4-F1).

    Args:
        path: Path da URL.

    Returns:
        LegacyGoneRoute ou None.
    """
    return match_legacy_gone(path, BOOKING_LEGACY_GONE_ROUTES)


def match_legacy_gone(
    path: str,
    routes: Optional[Tuple[LegacyGoneRoute, ...]] = None,
) -> Optional[LegacyGoneRoute]:
    """
    Encontra regra 410 para path legado (booking + payments).

    Args:
        path: Path da URL.
        routes: Conjunto de rotas (default: mapa completo R4-F9).

    Returns:
        LegacyGoneRoute ou None.
    """
    ordered = sorted(routes or LEGACY_GONE_ROUTES, key=lambda r: len(r.prefix), reverse=True)
    for rule in ordered:
        if path == rule.prefix or path.startswith(f"{rule.prefix}/"):
            return rule
    return None


def _gone_response(rule: LegacyGoneRoute) -> JSONResponse:
    """
    Monta resposta HTTP 410 Gone com headers ADR-033.

    Args:
        rule: Rota legado correspondente.

    Returns:
        JSONResponse 410.
    """
    detail = (
        f"Rota legado removida — use API CoreFlow v1 ({rule.successor})"
    )
    return JSONResponse(
        status_code=410,
        content={
            "type": "about:blank",
            "title": "Gone",
            "status": 410,
            "detail": detail,
            "message": detail,
            "successor": rule.successor,
            "enforcement": "gone",
        },
        headers={
            "Deprecation": "true",
            "Sunset": _SUNSET_HTTP_DATE,
            "Link": f'<{rule.successor}>; rel="successor-version"',
            "X-CoreFlow-Enforcement": "gone",
        },
    )


class LegacyGoneMiddleware(BaseHTTPMiddleware):
    """
    Middleware que responde 410 Gone em rotas legado (R4-F1 booking + R4-F9 payments).

    Args:
        app: Aplicação ASGI.
        enabled: Se False, pass-through.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Bloqueia paths legado (booking + pagamentos/sinal*) com 410.

        Args:
            request: Requisição HTTP.
            call_next: Próximo handler ASGI.

        Returns:
            JSONResponse 410 ou response normal.
        """
        if not self.enabled:
            return await call_next(request)

        rule = match_legacy_gone(request.url.path)
        if rule:
            return _gone_response(rule)
        return await call_next(request)
