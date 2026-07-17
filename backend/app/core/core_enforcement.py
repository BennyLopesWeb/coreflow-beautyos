"""
Core Enforcement — bloqueia ou avisa escritas em rotas legado (ADR-033 / R2-F6).

Modos: ``off`` | ``warn`` | ``block`` via ``CORE_ENFORCEMENT_MODE``.

Em ``block``, **apenas** escritas de booking legado são negadas (escopo narrow).
Payments/fila permanecem em warn até R3.
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


# Escopo NARROW R2-F6 — block applies ONLY to booking writes (ADR-033)
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

# Rotas adicionais: warn only até R3 (não entram no block F6)
_DEFERRED_WARN_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    LegacyWriteRoute("POST", "/payments/deposit", "/v1/payments"),
    LegacyWriteRoute("POST", "/payments/final", "/v1/payments"),
    LegacyWriteRoute("POST", "/fila", "/v1/waitlist"),
    LegacyWriteRoute("POST", "/pagamentos/sinal", "/v1/payments"),
    LegacyWriteRoute("POST", "/financeiro/saida", "/v1/invoices"),
)

# Compat: mapa completo para warn + documentação
LEGACY_WRITE_ROUTES: Tuple[LegacyWriteRoute, ...] = (
    BOOKING_LEGACY_WRITE_ROUTES + _DEFERRED_WARN_WRITE_ROUTES
)


def resolve_enforcement_mode() -> EnforcementMode:
    """
    Resolve modo efetivo de enforcement a partir das settings.

    Prioridade:
    1. ``CORE_ENFORCEMENT_ENABLED=true`` → block
    2. ``CORE_ENFORCEMENT_MODE`` explícito (off/warn/block)
    3. ``APP_ENV=staging`` → block (narrow booking)
    4. ``APP_ENV=production`` → block (fase final)
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
    Match apenas rotas booking (escopo block ADR-033).

    Args:
        method: Método HTTP.
        path: Path da URL.

    Returns:
        LegacyWriteRoute ou None.
    """
    return match_legacy_write(method, path, BOOKING_LEGACY_WRITE_ROUTES)


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


class CoreEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware de enforcement gradual para rotas legado.

    - ``off``: pass-through
    - ``warn``: headers Deprecation + permite request (booking + deferred)
    - ``block``: HTTP **409** só para booking legado (ADR-033); deferred passa

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
            Response normal, com headers warn, ou 409 (booking block).
        """
        if self.mode == "off" or request.method.upper() not in WRITE_METHODS:
            return await call_next(request)

        path = request.url.path
        method = request.method

        if self.mode == "block":
            booking_rule = match_booking_legacy_write(method, path)
            if booking_rule:
                _record_legacy_write_attempt("block", path)
                return JSONResponse(
                    status_code=409,
                    content={
                        "type": "about:blank",
                        "title": "Legacy write blocked",
                        "status": 409,
                        "detail": (
                            "Escrita legado de booking bloqueada — use API CoreFlow v1 "
                            f"({booking_rule.successor})"
                        ),
                        "message": (
                            "Escrita legado de booking bloqueada — use API CoreFlow v1 "
                            f"({booking_rule.successor})"
                        ),
                        "successor": booking_rule.successor,
                        "enforcement": "block",
                    },
                    headers=_enforcement_headers(booking_rule.successor, "block"),
                )
            # Payments/fila: não bloqueia em F6 — opcionalmente avisa
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
