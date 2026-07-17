"""R3-F1 — Enforcement block expandido (payments/fila) + production mode."""
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.core_enforcement import (
    BLOCKED_LEGACY_WRITE_ROUTES,
    BOOKING_LEGACY_WRITE_ROUTES,
    CoreEnforcementMiddleware,
    PAYMENTS_FILA_LEGACY_WRITE_ROUTES,
    match_blocked_legacy_write,
    match_booking_legacy_write,
    resolve_enforcement_mode,
)


def _app_with_routes(mode: str) -> Starlette:
    """
    App mínimo com booking, payments, fila e financeiro.

    Args:
        mode: Modo do middleware (off|warn|block).

    Returns:
        Starlette app com CoreEnforcementMiddleware.
    """

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/agenda/agendamentos", ok, methods=["POST", "PUT", "DELETE"]),
            Route("/reservations", ok, methods=["POST"]),
            Route("/payments/deposit", ok, methods=["POST"]),
            Route("/payments/final", ok, methods=["POST"]),
            Route("/pagamentos/sinal", ok, methods=["POST"]),
            Route("/fila", ok, methods=["POST"]),
            Route("/financeiro/saida", ok, methods=["POST"]),
        ]
    )
    app.add_middleware(CoreEnforcementMiddleware, mode=mode)
    return app


def test_block_denies_payments_and_fila_with_409():
    """Block R3-F1 nega payments e fila com 409 + successor v1."""
    with TestClient(_app_with_routes("block")) as client:
        pay = client.post("/payments/deposit", json={})
        assert pay.status_code == 409
        assert pay.json()["successor"] == "/v1/payments"
        assert pay.headers.get("X-CoreFlow-Enforcement") == "block"

        final = client.post("/payments/final", json={})
        assert final.status_code == 409

        sinal = client.post("/pagamentos/sinal", json={})
        assert sinal.status_code == 409
        assert sinal.json()["successor"] == "/v1/payments"

        fila = client.post("/fila", json={})
        assert fila.status_code == 409
        assert fila.json()["successor"] == "/v1/waitlist"
        assert "2028" in (fila.headers.get("Sunset") or "")


def test_block_still_denies_booking():
    """Booking legado continua bloqueado após expansão R3-F1."""
    with TestClient(_app_with_routes("block")) as client:
        response = client.post("/agenda/agendamentos", json={})
        assert response.status_code == 409
        assert response.json()["successor"] == "/v1/bookings"


def test_block_allows_financeiro_with_warn_headers():
    """Invoices/financeiro ainda não entram no block (warn only)."""
    with TestClient(_app_with_routes("block")) as client:
        response = client.post("/financeiro/saida", json={})
        assert response.status_code == 200
        assert response.headers.get("X-CoreFlow-Enforcement") == "warn"


def test_warn_rollback_allows_payments():
    """Rollback warn: payments/fila passam com headers deprecation."""
    with TestClient(_app_with_routes("warn")) as client:
        pay = client.post("/payments/deposit", json={})
        assert pay.status_code == 200
        assert pay.headers.get("X-CoreFlow-Enforcement") == "warn"
        fila = client.post("/fila", json={})
        assert fila.status_code == 200


def test_blocked_routes_include_booking_payments_fila():
    """Mapa block R3-F1 = booking ∪ payments/fila."""
    assert match_blocked_legacy_write("POST", "/payments/deposit") is not None
    assert match_blocked_legacy_write("POST", "/fila") is not None
    assert match_blocked_legacy_write("POST", "/financeiro/saida") is None
    assert match_booking_legacy_write("POST", "/payments/deposit") is None
    assert len(BLOCKED_LEGACY_WRITE_ROUTES) == (
        len(BOOKING_LEGACY_WRITE_ROUTES) + len(PAYMENTS_FILA_LEGACY_WRITE_ROUTES)
    )


def test_production_env_resolves_to_block(monkeypatch):
    """
    APP_ENV=production sem modo explícito resolve para block (piloto R3-F1).

    Args:
        monkeypatch: Fixture pytest para settings.
    """
    from app.core import config as config_mod
    from app.core import core_enforcement as enf

    monkeypatch.setattr(config_mod.settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(config_mod.settings, "CORE_ENFORCEMENT_MODE", "")
    monkeypatch.setattr(config_mod.settings, "APP_ENV", "production")
    assert resolve_enforcement_mode() == "block"
    # reimport path uses settings singleton — call again after patch
    assert enf.resolve_enforcement_mode() == "block"
