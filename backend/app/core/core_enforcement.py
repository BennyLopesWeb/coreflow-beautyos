"""
Core Enforcement — bloqueia ou avisa escritas em rotas legado (ADR-033 / R3-F1).

Modos: ``off`` | ``warn`` | ``block`` via ``CORE_ENFORCEMENT_MODE``.

Em ``block`` (R3-F1): escritas legado de **booking + payments + fila** → HTTP 409.
Invoices (``/financeiro/saida``) permanecem em warn até fase seguinte.
"""
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Sequence, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

EnforcementMode = Literal["off", "warn", "block"]

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# RFC 8594 / ADR-033
_SUNSET_HTTP_DATE = "Sat, 01 Jan 2028 00:00:00 GMT"


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


# Escopo booking — block desde R2-F6 (ADR-033)
BOOKING_LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    LegacyWriteRoute("POST", "/agenda/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("PUT", "/agenda/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("DELETE", "/agenda/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("POST", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("PUT", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("DELETE", "/agendamentos", "/v1/bookings"),
    LegacyWriteRoute("POST", "/reservations", "/v1/bookings"),
    LegacyWriteRoute("PUT", "/reservations", "/v1/bookings"),
    LegacyWriteRoute("DELETE", "/reservations", "/v1/bookings"),
)

# Escopo payments + fila — block a partir de R3-F1 (ADR-033 §R3)
PAYMENTS_FILA_LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    LegacyWriteRoute("POST", "/payments/deposit", "/v1/payments"),
    LegacyWriteRoute("POST", "/payments/final", "/v1/payments"),
    LegacyWriteRoute("POST", "/pagamentos/sinal", "/v1/payments"),
    LegacyWriteRoute("POST", "/fila", "/v1/waitlist"),
)

# União: rotas que recebem 409 em modo block (staging/production)
BLOCKED_LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    BOOKING_LEGACY_WRITE_ROUTES + PAYMENTS_FILA_LEGACY_WRITE_ROUTES
)

# Ainda só warn em block (próximas fases)
_DEFERRED_WARN_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    LegacyWriteRoute("POST", "/financeiro/saida", "/v1/invoices"),
)

# Compat: mapa completo para warn + documentação
LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    BLOCKED_LEGACY_WRITE_ROUTES + _DEFERRED_WARN_WRITE_ROUTES
)


def resolve_enforcement_mode() -> EnforcementMode:
    """
    Resolve modo efetivo de enforcement a partir das settings.

    Prioridade:
    1. ``CORE_ENFORCEMENT_ENABLED=true`` → block
    2. ``CORE_ENFORCEMENT_MODE`` explícito (off/warn/block)
    3. ``APP_ENV=staging`` → block (booking + payments + fila)
    4. ``APP_ENV=production`` → block (piloto R3-F1)
    5. off (com warn opcional em development se WARN_ENABLED)

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


def match_legacy_write(
    method: str,
    path: str,
    routes: Optional[Sequence[LegacyWriteRoute]] = None,
) -> Optional[LegacyWriteRoute]:
    """
    Encontra regra de enforcement para método + path.

    Args:
        method: Método HTTP da requisição.
        path: Path da URL.
        routes: Conjunto de rotas (default: mapa completo warn).

    Returns:
        LegacyWriteRoute correspondente ou None.
    """
    for rule in routes or LEGACY_WRITE_ROUTES:
        if rule.method != method.upper():
            continue
        if path == rule.prefix or path.startswith(f"{rule.prefix}/"):
            return rule
    return None


def match_booking_legacy_write(method: str, path: str) -> Optional[LegacyWriteRoute]:
    """
    Match apenas rotas booking (escopo R2-F6).

    Args:
        method: Método HTTP.
        path: Path da URL.

    Returns:
        LegacyWriteRoute ou None.
    """
    return match_legacy_write(method, path, BOOKING_LEGACY_WRITE_ROUTES)


def match_blocked_legacy_write(method: str, path: str) -> Optional[LegacyWriteRoute]:
    """
    Match rotas com block ativo em R3-F1 (booking + payments + fila).

    Args:
        method: Método HTTP.
        path: Path da URL.

    Returns:
        LegacyWriteRoute ou None.
    """
    return match_legacy_write(method, path, BLOCKED_LEGACY_WRITE_ROUTES)


def _record_legacy_write_attempt(mode: str, path: str) -> None:
    """
    Registra tentativa de escrita legado (métrica in-process).

    Args:
        mode: warn | block.
        path: Path HTTP.

    Returns:
        None
    """
    try:
        from app.core.architecture_metrics import ArchitectureMetricsStore

        ArchitectureMetricsStore.get().record_legacy_write_attempt(mode, path)
    except Exception:
        pass


def _enforcement_headers(successor: str, mode: str) -> dict:
    """
    Headers ADR-033 para warn/block.

    Args:
        successor: Path v1.
        mode: warn | block.

    Returns:
        Dict de headers HTTP.
    """
    return {
        "Deprecation": "true",
        "Sunset": _SUNSET_HTTP_DATE,
        "Link": f'<{successor}>; rel="successor-version"',
        "X-CoreFlow-Enforcement": mode,
        "CoreFlow-Enforcement": mode,
    }


def _blocked_response(rule: LegacyWriteRoute) -> JSONResponse:
    """
    Monta resposta HTTP 409 para escrita legado bloqueada.

    Args:
        rule: Rota legado correspondente.

    Returns:
        JSONResponse 409 com Problem Details e headers ADR-033.
    """
    detail = (
        f"Escrita legado bloqueada — use API CoreFlow v1 ({rule.successor})"
    )
    return JSONResponse(
        status_code=409,
        content={
            "type": "about:blank",
            "title": "Legacy write blocked",
            "status": 409,
            "detail": detail,
            "message": detail,
            "successor": rule.successor,
            "enforcement": "block",
        },
        headers=_enforcement_headers(rule.successor, "block"),
    )


class CoreEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware de enforcement gradual para rotas legado.

    - ``off``: pass-through
    - ``warn``: headers Deprecation + permite request (mapa completo)
    - ``block``: HTTP **409** para booking + payments + fila (R3-F1);
      ``/financeiro/saida`` só recebe warn headers

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
            Response normal, com headers warn, ou 409 (block R3-F1).
        """
        if self.mode == "off" or request.method.upper() not in WRITE_METHODS:
            return await call_next(request)

        path = request.url.path
        method = request.method

        if self.mode == "block":
            blocked = match_blocked_legacy_write(method, path)
            if blocked:
                _record_legacy_write_attempt("block", path)
                return _blocked_response(blocked)
            deferred = match_legacy_write(method, path, _DEFERRED_WARN_WRITE_ROUTES)
            if deferred:
                _record_legacy_write_attempt("warn", path)
                response = await call_next(request)
                for key, val in _enforcement_headers(deferred.successor, "warn").items():
                    response.headers[key] = val
                return response
            return await call_next(request)

        # warn: todas as rotas do mapa completo
        rule = match_legacy_write(method, path, LEGACY_WRITE_ROUTES)
        if not rule:
            return await call_next(request)

        _record_legacy_write_attempt("warn", path)
        response = await call_next(request)
        for key, val in _enforcement_headers(rule.successor, "warn").items():
            response.headers[key] = val
        return response


def enforcement_enabled() -> bool:
    """
    Indica se enforcement está ativo (warn ou block).

    Returns:
        True se modo não é off.
    """
    return resolve_enforcement_mode() != "off"
