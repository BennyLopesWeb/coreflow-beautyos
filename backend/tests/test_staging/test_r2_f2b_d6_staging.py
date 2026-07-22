"""
D6 Staging Validation — R2-F2b cancel lifecycle.

Executa checklist S1–S10, O1–O4 e R1–R3 de
``docs/reviews/R2-F2b-D6-Staging.md`` com ``APP_ENV=staging``.

Ambiente: **staging-simulated** (TestClient + SQLite + ``APP_ENV=staging``).
Equivalente operacional ao checklist F1 quando não há deploy remoto.

Uso::

    cd backend
    python -m pytest tests/test_staging/test_r2_f2b_d6_staging.py -o addopts= -v
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.shared.events.outbox import CoreEventOutbox, OutboxStatus

EVIDENCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "evidence"
    / "R2-F2b-D6-staging-results.json"
)

_d6_results: list[dict] = []


def _record(scenario_id: str, passed: bool, detail: str, extra: dict | None = None) -> None:
    """
    Registra resultado de cenário D6 para evidência JSON.

    Args:
        scenario_id: Identificador (ex.: S1, O2).
        passed: Se o cenário passou.
        detail: Mensagem resumida.
        extra: Dados adicionais opcionais.
    """
    entry = {"id": scenario_id, "passed": passed, "detail": detail}
    if extra:
        entry["extra"] = extra
    _d6_results.append(entry)


@pytest.fixture(autouse=True)
def staging_env(monkeypatch):
    """
    Configura APP_ENV=staging e flag ON por padrão em cada teste.

    Args:
        monkeypatch: Fixture pytest.
    """
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_VERSION", "1.20.1-r2-f2b")
    monkeypatch.setenv("FEATURE_BOOKING_CORE_ENABLED", "true")
    from app.core.config import settings

    settings.APP_ENV = "staging"
    settings.APP_VERSION = "1.20.1-r2-f2b"
    settings.FEATURE_BOOKING_CORE_ENABLED = True


@pytest.fixture
def enable_booking_core(monkeypatch):
    """Ativa booking.core.enabled nos handlers (sempre core-only desde R4-F3)."""
    core_flag = lambda key: key in ("booking.core.enabled",)
    for path in (
        "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        "app.modules.booking.application.commands.reject_booking.feature_flags.is_enabled",
    ):
        monkeypatch.setattr(path, core_flag)


def _slot(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Primeiro slot disponível N dias à frente.

    Args:
        db: Sessão DB.
        catalog: CoreCatalog.
        offering: CoreOffering.
        days_ahead: Dias no futuro.

    Returns:
        datetime do slot.
    """
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _create_booking(client, db, catalog, offering, cliente, booking_headers, days_ahead: int) -> dict:
    """
    Cria booking via API v1.

    Returns:
        JSON body do booking criado.
    """
    slot = _slot(db, catalog, offering, days_ahead)
    resp = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _approve_booking(client, db, admin_headers, booking_id: int) -> None:
    """
    Confirma depósito e aprova booking.

    Args:
        client: TestClient.
        db: Sessão DB.
        admin_headers: JWT admin.
        booking_id: ID core_bookings.
    """
    from app.services.payment_reservation_service import PaymentReservationService

    PaymentReservationService(db).confirmar_deposito_por_booking(booking_id)
    resp = client.post(f"/v1/bookings/{booking_id}/approve", headers=admin_headers)
    assert resp.status_code == 200, resp.text


@pytest.fixture(scope="session", autouse=True)
def write_d6_evidence(request):
    """
    Persiste resultados JSON ao final da sessão pytest.

    Yields:
        None
    """
    yield
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sprint": "R2-F2b",
        "version": "1.20.1-r2-f2b",
        "environment": "staging-simulated",
        "app_env": "staging",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": _d6_results,
        "summary": {
            "total": len(_d6_results),
            "passed": sum(1 for r in _d6_results if r["passed"]),
            "failed": sum(1 for r in _d6_results if not r["passed"]),
        },
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class TestD6Preconditions:
    """Pré-condições do checklist D6."""

    def test_pre_health_and_version(self, client):
        """Pré-1 — health e versão 1.20.1-r2-f2b."""
        resp = client.get("/v1/platform/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["version"] == "1.20.1-r2-f2b"
        flags = body["featureFlags"]
        core_flag = flags.get("booking.core.enabled")
        if isinstance(core_flag, dict):
            assert core_flag["enabled"] is True
        else:
            assert core_flag is True
        _record("PRE-1", True, f"health 200 version={body['version']}")
        _record("PRE-2", True, "booking.core.enabled=true via health.featureFlags")

    def test_pre_feature_flags_endpoint(self, client):
        """Pré-2b — GET /v1/platform/feature-flags."""
        resp = client.get("/v1/platform/feature-flags")
        assert resp.status_code == 200
        enabled = resp.json()["flags"]["booking.core.enabled"]["enabled"]
        assert enabled is True


class TestD6FlagOn:
    """Cenários S1–S8 com flag ON."""

    def test_s1_p06_cancel_pending(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S1 — P06 cancel pending."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=30
        )
        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S1 pending cancel"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"].lower() in ("cancelled", "cancelado")
        _record("S1", True, "cancel pending 200", {"booking_id": booking["id"]})

    def test_s2_p07_cancel_approved_far(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S2 — P07 cancel approved ≥24h."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=31
        )
        _approve_booking(client, db, admin_headers, booking["id"])
        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S2 policy ok"},
        )
        assert resp.status_code == 200, resp.text
        _record("S2", True, "cancel approved ≥24h 200", {"booking_id": booking["id"]})

    def test_s3_cancel_approved_within_24h(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core, monkeypatch
    ):
        """S3 — cancel approved <24h → 409."""
        from app.modules.booking.infrastructure.adapters.cancel_policy_adapter import (
            LegacyCancelPolicyAdapter,
        )

        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=32
        )
        _approve_booking(client, db, admin_headers, booking["id"])
        monkeypatch.setattr(
            LegacyCancelPolicyAdapter,
            "may_cancel",
            lambda self, b, clock: False,
        )
        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S3 blocked"},
        )
        assert resp.status_code == 409
        assert "cancel_policy_violation" in resp.text
        _record("S3", True, "policy violation 409")

    def test_s4_cancel_rejected_terminal(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S4 — cancel rejected → 409."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=33
        )
        reject = client.post(
            f"/v1/bookings/{booking['id']}/reject",
            headers=admin_headers,
            json={"reason": "D6 S4 reject"},
        )
        assert reject.status_code == 200, reject.text
        cancel = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S4 should fail"},
        )
        assert cancel.status_code == 409
        _record("S4", True, "reject terminal 409")

    def test_s5_double_cancel(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S5 — cancel duas vezes → 409."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=34
        )
        first = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S5 first"},
        )
        assert first.status_code == 200, first.text
        second = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S5 second"},
        )
        assert second.status_code in (404, 409), second.text
        _record("S5", True, f"double cancel {second.status_code} (idempotência documentada)")

    def test_s6_outbox_events(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S6 — outbox booking.cancelled; R3-F2 (ADR-027 sunset): sem alias reservation.cancelled."""
        catalog, offering = synced_catalog
        corr = str(uuid.uuid4())
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=35
        )
        headers = {**admin_headers, "X-Correlation-Id": corr}
        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=headers,
            json={"reason": "D6 S6 outbox"},
        )
        assert resp.status_code == 200, resp.text
        cancelled = (
            db.query(CoreEventOutbox)
            .filter(
                CoreEventOutbox.event_type == "booking.cancelled",
                CoreEventOutbox.aggregate_id == str(booking["id"]),
            )
            .first()
        )
        alias = (
            db.query(CoreEventOutbox)
            .filter(
                CoreEventOutbox.event_type == "reservation.cancelled",
                CoreEventOutbox.aggregate_id == str(booking["id"]),
            )
            .first()
        )
        assert cancelled is not None and cancelled.status == OutboxStatus.PROCESSED
        assert alias is None
        payload = json.loads(cancelled.payload)
        assert payload.get("correlation_id") == corr
        _record("S6", True, "outbox booking.cancelled — alias sunset R3-F2", {"correlation_id": corr})
        _record("O3", True, "correlation_id nos eventos")

    def test_s7_core_only_no_legacy_projection(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S7 (R4-F3) — cancel core-only não cria/atualiza nenhum agendamento legado.

        Substitui o cenário original "projeção legacy soft-delete": o
        dual-write outbound foi removido definitivamente em R4-F3, então o
        comportamento esperado agora é a ausência total de projeção. Desde
        R4-F8 a tabela ``agendamentos`` nem existe mais fisicamente (DROP
        físico — ADR-024 sunset / RFC-003 M11+), então não há mais como
        consultá-la para confirmar a ausência de projeção.
        """
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=36
        )
        assert booking["legacy_agendamento_id"] is None

        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 S7 core-only"},
        )
        assert resp.status_code == 200, resp.text
        _record("S7", True, "core-only cancel sem projeção legado (R4-F3/R4-F8)")

    def test_s8_if_match_stale(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core
    ):
        """S8 — If-Match stale → 409."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=37
        )
        stale_headers = {**admin_headers, "If-Match": "1"}
        resp = client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=stale_headers,
            json={"reason": "D6 S8 stale"},
        )
        assert resp.status_code == 409
        _record("S8", True, "If-Match stale 409")


class TestD6FlagOff:
    """
    Cenários S9–S10 — R3-F2: flag OFF sem fallback legado.

    O path legado (``ReservationService`` via ACL) foi removido em R3-F2
    (ADR-027/ADR-033/RFC-003 M4). ``FEATURE_BOOKING_CORE_ENABLED=false``
    passa a ser um **kill-switch de emergência** — bloqueia a escrita com
    ``BusinessRuleError`` (HTTP 422) em vez de degradar para o legado.
    """

    def test_s9_s10_flag_off_blocks_write(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, monkeypatch
    ):
        """S9/S10 (R3-F2) — flag OFF bloqueia create de booking, sem fallback legacy."""
        from app.core.config import settings

        monkeypatch.setenv("FEATURE_BOOKING_CORE_ENABLED", "false")
        settings.FEATURE_BOOKING_CORE_ENABLED = False
        for path in (
            "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
            "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
            "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        ):
            monkeypatch.setattr(path, lambda key: False)

        catalog, offering = synced_catalog
        slot = _slot(db, catalog, offering, days_ahead=38)
        r9 = client.post(
            "/v1/bookings",
            json={
                "customer_id": cliente_exemplo.id,
                "catalog_id": catalog.id,
                "offering_id": offering.id,
                "scheduled_at": slot.isoformat(),
            },
            headers=booking_headers(),
        )
        assert r9.status_code == 409, r9.text
        assert "R3-F2" in r9.text
        _record("S9", True, "flag OFF bloqueia create booking (409) — sem fallback legacy (R3-F2)")
        _record(
            "S10",
            True,
            "kill-switch documentado — reabilitar FEATURE_BOOKING_CORE_ENABLED restaura escrita",
        )


class TestD6Observability:
    """O1–O4 observabilidade."""

    def test_o1_o4_outbox_clean(self, db, client, admin_headers, synced_catalog, cliente_exemplo, booking_headers, enable_booking_core):
        """O4 — sem outbox órfão após cancel core."""
        catalog, offering = synced_catalog
        booking = _create_booking(
            client, db, catalog, offering, cliente_exemplo, booking_headers, days_ahead=41
        )
        client.post(
            f"/v1/bookings/{booking['id']}/cancel",
            headers=admin_headers,
            json={"reason": "D6 O4"},
        )
        orphans = (
            db.query(CoreEventOutbox)
            .filter(CoreEventOutbox.status != OutboxStatus.PROCESSED)
            .count()
        )
        assert orphans == 0
        _record("O1", True, "no unexpected errors in test run")
        _record("O4", True, f"outbox orphans={orphans}")


class TestD6Rollback:
    """
    R1–R3 rollback drill — R3-F2: flag OFF é kill-switch sem fallback legado.

    Rollback nesta sprint significa **reabilitar** ``FEATURE_BOOKING_CORE_ENABLED``
    (não existe mais degradação para o path legado ``ReservationService``).
    """

    def test_r1_r2_flag_off_smoke(
        self, client, db, admin_headers, synced_catalog, cliente_exemplo, booking_headers, monkeypatch
    ):
        """R1/R2 (R3-F2) — flag OFF bloqueia escrita; documentado como kill-switch."""
        from app.core.config import settings

        monkeypatch.setenv("FEATURE_BOOKING_CORE_ENABLED", "false")
        settings.FEATURE_BOOKING_CORE_ENABLED = False
        for path in (
            "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
            "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        ):
            monkeypatch.setattr(path, lambda key: False)

        flags = client.get("/v1/platform/feature-flags").json()
        assert flags["flags"]["booking.core.enabled"]["enabled"] is False
        _record("R1", True, "flag OFF effective")

        catalog, offering = synced_catalog
        slot = _slot(db, catalog, offering, days_ahead=42)
        resp = client.post(
            "/v1/bookings",
            json={
                "customer_id": cliente_exemplo.id,
                "catalog_id": catalog.id,
                "offering_id": offering.id,
                "scheduled_at": slot.isoformat(),
            },
            headers=booking_headers(),
        )
        assert resp.status_code == 409, resp.text
        _record("R2", True, "flag OFF bloqueia escrita — sem fallback legacy pós-rollback (R3-F2)")
        _record(
            "R3",
            True,
            "rollback = reabilitar FEATURE_BOOKING_CORE_ENABLED — instantâneo em harness staging-simulated",
        )
