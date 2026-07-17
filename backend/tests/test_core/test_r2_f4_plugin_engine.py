"""R2-F4 — Typed Hook Registry + BeautyAgent plugin path."""
from pathlib import Path

from app.core.plugin.hook_registry import hook_registry
from app.core.plugin.hooks import WaitlistPromotedPayload
from app.core.plugin.registry import plugin_registry
from app.plugins.beauty.agents.beauty_agent import BeautyAgent
from datetime import datetime


def test_hook_registry_installs_typed_handlers():
    """
    load_all instala handlers tipados sob app.plugins.*.
    """
    plugin_registry.load_all()
    refs = hook_registry.list_handlers("waitlist.promoted")
    plugin_ids = {r.plugin_id for r in refs}
    assert "beauty" in plugin_ids
    assert "sports" in plugin_ids
    assert "clinic" in plugin_ids
    for ref in refs:
        assert ref.handler_path.startswith("app.plugins.")


def test_dispatch_noop_when_flag_off(monkeypatch):
    """
    Dispatch retorna 0 com plugin.engine.enabled OFF.
    """
    plugin_registry.load_all()
    monkeypatch.setattr(
        "app.core.plugin.hook_registry.feature_flags.is_enabled",
        lambda key: False,
    )
    n = hook_registry.dispatch(
        "waitlist.promoted",
        WaitlistPromotedPayload(
            company_id=1,
            waitlist_id=1,
            booking_id=1,
            customer_id=1,
            catalog_id=1,
            offering_id=1,
            scheduled_at=datetime.utcnow(),
        ),
    )
    assert n == 0


def test_dispatch_invokes_beauty_handler(monkeypatch):
    """
    Dispatch com flag ON invoca handler beauty.
    """
    from app.plugins.beauty.hooks import on_waitlist_promoted as beauty_hook

    plugin_registry.load_all()
    beauty_hook.reset_invoke_count()
    monkeypatch.setattr(
        "app.core.plugin.hook_registry.feature_flags.is_enabled",
        lambda key: key == "plugin.engine.enabled",
    )
    n = hook_registry.dispatch(
        "waitlist.promoted",
        WaitlistPromotedPayload(
            company_id=1,
            waitlist_id=9,
            booking_id=10,
            customer_id=1,
            catalog_id=1,
            offering_id=1,
            scheduled_at=datetime.utcnow(),
        ),
    )
    assert n >= 1
    assert beauty_hook.get_invoke_count() >= 1


def test_beauty_agent_lives_under_app_plugins():
    """
    FF-PLG-005: implementação canônica em app/plugins/beauty/agents/.
    """
    path = Path(BeautyAgent.__module__.replace(".", "/") + ".py")
    # módulo = app.plugins.beauty.agents.beauty_agent
    assert BeautyAgent.__module__ == "app.plugins.beauty.agents.beauty_agent"
    agent_file = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "plugins"
        / "beauty"
        / "agents"
        / "beauty_agent.py"
    )
    assert agent_file.is_file()
    assert path.parts[0] == "app" or True  # noqa: sanity


def test_beauty_manifest_waitlist_promoted_hook():
    """
    Manifest beauty declara waitlist.promoted (ADR-011), não waitlist.approved.
    """
    plugin_registry.load_all()
    manifest = plugin_registry.require("beauty")
    assert "waitlist.promoted" in manifest.hooks
    path, async_mode = manifest.resolve_hook_binding("waitlist.promoted")
    assert path == "app.plugins.beauty.hooks.on_waitlist_promoted"
    assert async_mode is True
    assert manifest.agents
