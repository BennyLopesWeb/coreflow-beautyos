"""
Core Enforcement — bloqueia ou avisa sobre escritas em rotas legado (Fase B).

Modos: ``off`` | ``warn`` | ``block`` via ``CORE_ENFORCEMENT_MODE``.
"""
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

EnforcementMode = Literal["off", "warn", "block"]

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class LegacyWriteRoute:
    """
    Rota legado de escrita bloqueada ou avisada quando enforcement ativo.

    Attributes:
        method: Método HTTP (POST, PUT…).
        prefix: Prefixo do path.
        successor: Rota CoreFlow v1 sucessora.
    """

    method: str
    prefix: str
    successor: str


LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    LegacyWriteRoute("POST", "/agenda/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("POST", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("PUT", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("DELETE", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("POST", "/reservations", "/v1/bookings"),
    LegacyWriteRoute("PUT", "/reservations", "/v1/bookings"),
    LegacyWriteRoute("POST", "/payments/deposit", "/v1/payments"),
    LegacyWriteRoute("POST", "/payments/final", "/v1/payments"),
    LegacyWriteRoute("POST", "/fila", "/v1/waitlist"),
    LegacyWriteRoute("POST", "/pagamentos/sinal", "/v1/payments"),
    LegacyWriteRoute("POST", "/financeiro/saida", "/v1/invoices"),
)


def resolve_enforcement_mode() -> EnforcementMode:
    """
    Resolve modo efetivo de enforcement a partir das settings.

    Prioridade:
    1. ``CORE_ENFORCEMENT_ENABLED=true`` → block
    2. ``CORE_ENFORCEMENT_MODE`` explícito (off/warn/block)
    3. ``APP_ENV=staging`` → block
    4. ``APP_ENV=production`` → block (fase final CF-12)
    5. off

    Returns:
        off, warn ou block.
    """
    if settings.CORE_ENFORCEMENT_ENABLED:
        return "block"
    explicit = (settings.CORE_ENFORCEMENT_MODE or "").lower()
    if explicit == "warn":
        return "warn"
    if explicit == "block":
        return "block"
    env = settings.APP_ENV.lower()
    if explicit == "off":
        if settings.CORE_ENFORCEMENT_WARN_ENABLED and env in ("development", "staging"):
            return "warn"
        return "off"
    if env == "staging":
        return "block"
    if env == "production":
        return "block"
    return "off"


def match_legacy_write(method: str, path: str) -> Optional[LegacyWriteRoute]:
    """
    Encontra regra de enforcement para método + path.

    Args:
        method: Método HTTP da requisição.
        path: Path da URL.

    Returns:
        LegacyWriteRoute correspondente ou None.
    """
    for rule in LEGACY_WRITE_ROUTES:
        if rule.method != method.upper():
            continue
        if path == rule.prefix or path.startswith(f"{rule.prefix}/"):
            return rule
    return None


class CoreEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware de enforcement gradual para rotas legado.

    - ``off``: pass-through
    - ``warn``: headers Deprecation + X-CoreFlow-Enforcement, permite request
    - ``block``: HTTP 403 com link para sucessor v1

    Args:
        app: Aplicação ASGI.
        mode: Modo de enforcement (default resolve_enforcement_mode()).
    """

    def __init__(self, app, mode: Optional[EnforcementMode] = None):
        super().__init__(app)
        self.mode = mode or resolve_enforcement_mode()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Aplica enforcement conforme modo configurado.

        Args:
            request: Requisição HTTP.
            call_next: Próximo handler ASGI.

        Returns:
            Response normal, com headers warn, ou 403.
        """
        if self.mode == "off" or request.method.upper() not in WRITE_METHODS:
            return await call_next(request)

        rule = match_legacy_write(request.method, request.url.path)
        if not rule:
            return await call_next(request)

        if self.mode == "block":
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "Escrita legado bloqueada — use API CoreFlow v1 "
                        f"({rule.successor})"
                    ),
                    "successor": rule.successor,
                    "enforcement": "block",
                },
                headers={
                    "Link": f'<{rule.successor}>; rel="successor-version"',
                    "X-CoreFlow-Enforcement": "block",
                },
            )

        response = await call_next(request)
        response.headers["Deprecation"] = "true"
        response.headers["Link"] = f'<{rule.successor}>; rel="successor-version"'
        response.headers["X-CoreFlow-Enforcement"] = "warn"
        return response


def enforcement_enabled() -> bool:
    """
    Indica se enforcement está ativo (warn ou block).

    Returns:
        True se modo não é off.
    """
    return resolve_enforcement_mode() != "off"
