"""R2-F4 — Paridade P10 waitlist → booking + plugin hook."""
from datetime import date, datetime, timedelta

import pytest

from app.models.fila import Fila, StatusFila
from app.modules.catalog.application.legacy_sync_service import LegacySyncService
from app.modules.customer.legacy_sync import CustomerLegacySyncService
from app.modules.waitlist.application.legacy_sync_service import WaitlistLegacySyncService
from app.modules.waitlist.domain.models import CoreWaitlist, CoreWaitlistStatus
from app.plugins.beauty.hooks import on_waitlist_promoted as beauty_hook
from app.core.plugin.registry import plugin_registry


@pytest.fixture
def enable_booking_and_plugin(monkeypatch):
    """Ativa booking.core + plugin.engine para path F4/P10."""

    def _is_enabled(key: str) -> bool:
        return key in ("booking.core.enabled", "plugin.engine.enabled")

    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        _is_enabled,
    )
    monkeypatch.setattr(
        "app.core.plugin.hook_registry.feature_flags.is_enabled",
        _is_enabled,
    )


@pytest.fixture
def enable_booking_plugin_off(monkeypatch):
    """Booking ON, plugin engine OFF — booking criado, hook não dispara."""

    def _is_enabled(key: str) -> bool:
        return key == "booking.core.enabled"

    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        _is_enabled,
    )
    monkeypatch.setattr(
        "app.core.plugin.hook_registry.feature_flags.is_enabled",
        _is_enabled,
    )


def _seed_waitlist(db, default_company, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """
    Cria fila legado + sync catalog/customer/waitlist.

    Returns:
        CoreWaitlist waiting.
    """
    LegacySyncService(db).sync_all()
    CustomerLegacySyncService(db).sync_all()
    fila = Fila(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data=date.today() + timedelta(days=3),
        posicao=1,
        status=StatusFila.WAITING,
        observacoes="P10",
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)
    WaitlistLegacySyncService(db).sync_all()
    item = (
        db.query(CoreWaitlist)
        .filter(CoreWaitlist.legacy_fila_id == fila.id)
        .first()
    )
    assert item is not None
    assert item.catalog_id is not None
    assert item.offering_id is not None
    return item


def test_p10_waitlist_promote_hook_on(
    client,
    admin_headers,
    db,
    default_company,
    cliente_exemplo,
    tranca_exemplo,
    service_image_exemplo,
    enable_booking_and_plugin,
):
    """P10 — promote cria booking e dispara hook waitlist.promoted (flag ON)."""
    plugin_registry.load_all()
    beauty_hook.reset_invoke_count()
    item = _seed_waitlist(
        db, default_company, cliente_exemplo, tranca_exemplo, service_image_exemplo
    )
    starts = (datetime.now() + timedelta(days=4)).replace(
        hour=11, minute=0, second=0, microsecond=0
    )
    response = client.post(
        f"/v1/waitlist/{item.id}/promote",
        json={"scheduled_at": starts.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["booking_id"] > 0
    assert body["hook_dispatched"] >= 1
    assert body["waitlist"]["status"] in (
        CoreWaitlistStatus.APPROVED.value,
        "approved",
    )
    assert body["waitlist"]["booking_id"] == body["booking_id"]
    assert beauty_hook.get_invoke_count() >= 1


def test_p10_waitlist_promote_hook_off(
    client,
    admin_headers,
    db,
    default_company,
    cliente_exemplo,
    tranca_exemplo,
    service_image_exemplo,
    enable_booking_plugin_off,
):
    """P10 — promote cria booking; hook não dispara com plugin engine OFF."""
    plugin_registry.load_all()
    beauty_hook.reset_invoke_count()
    item = _seed_waitlist(
        db, default_company, cliente_exemplo, tranca_exemplo, service_image_exemplo
    )
    starts = (datetime.now() + timedelta(days=5)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    response = client.post(
        f"/v1/waitlist/{item.id}/promote",
        json={"scheduled_at": starts.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["booking_id"] > 0
    assert body["hook_dispatched"] == 0
    assert beauty_hook.get_invoke_count() == 0
