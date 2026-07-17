"""R2-F6 — Enforcement block narrow (ADR-033) + rollback warn."""
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.core_enforcement import (
    BOOKING_LEGACY_WRITE_ROUTES,
    CoreEnforcementMiddleware,
    match_booking_legacy_write,
    match_legacy_write,
)


def _app_with_routes(mode: str) -> Starlette:
    """
    App mínimo com booking + payments + fila.

    Args:
        mode: Modo do middleware.

    Returns:
        Starlette app.
    """

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/agenda/agendamentos", ok, methods=["POST", "PUT", "DELETE"]),
            Route("/reservations", ok, methods=["POST"]),
            Route("/payments/deposit", ok, methods=["POST"]),
            Route("/fila", ok, methods=["POST"]),
        ]
    )
    app.add_middleware(CoreEnforcementMiddleware, mode=mode)
    return app


def test_block_denies_booking_legacy_with_409():
    """Block nega POST booking legado com 409 + headers ADR-033."""
    with TestClient(_app_with_routes("block")) as client:
        response = client.post("/agenda/agendamentos", json={})
        assert response.status_code == 409
        body = response.json()
        assert body["successor"] == "/v1/bookings"
        assert body["enforcement"] == "block"
        assert response.headers.get("Deprecation") == "true"
        assert "2028" in (response.headers.get("Sunset") or "")
        assert response.headers.get("X-CoreFlow-Enforcement") == "block"


def test_warn_allows_booking_with_headers():
    """Rollback warn: booking legado passa com headers."""
    with TestClient(_app_with_routes("warn")) as client:
        response = client.post("/reservations", json={})
        assert response.status_code == 200
        assert response.headers.get("X-CoreFlow-Enforcement") == "warn"


def test_booking_routes_cover_agenda_and_reservations():
    """Mapa narrow cobre prefixes booking."""
    assert match_booking_legacy_write("POST", "/agenda/agendamentos") is not None
    assert match_booking_legacy_write("DELETE", "/agendamentos/1") is not None
    assert match_booking_legacy_write("POST", "/reservations") is not None
    assert match_booking_legacy_write("POST", "/payments/deposit") is None
    assert len(BOOKING_LEGACY_WRITE_ROUTES) >= 6
    assert match_legacy_write("POST", "/payments/deposit") is not None


def test_parity_matrix_twelve_scenarios_documented():
    """Gate F6: matriz de paridade declara 12 cenários (P01–P12)."""
    from pathlib import Path

    matrix = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "architecture"
        / "R2-ParityMatrix.md"
    )
    text = matrix.read_text(encoding="utf-8")
    for pid in ("P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10", "P11", "P12"):
        assert pid in text
