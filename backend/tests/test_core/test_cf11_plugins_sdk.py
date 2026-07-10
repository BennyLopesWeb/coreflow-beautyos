"""Testes CF-11 — plugins verticais + SDK registry + production enforcement."""
from app.core.core_enforcement import resolve_enforcement_mode
from app.core.config import settings
from app.core.plugin.registry import plugin_registry
from app.modules.marketplace.application.marketplace_service import MarketplaceService


def test_plugin_registry_loads_three_plugins():
    """Registry carrega beauty, sports e clinic (manifests locais CF-11)."""
    plugin_registry.load_all()
    ids = {p.plugin_id for p in plugin_registry.list_all()}
    assert "beauty" in ids
    assert "sports" in ids
    assert "clinic" in ids


def test_sports_plugin_terminology():
    """Plugin sports expõe terminologia esportiva."""
    manifest = plugin_registry.require("sports")
    assert manifest.term("worker") == "Árbitro"
    assert manifest.term("resource") == "Quadra"
    assert manifest.has_feature("operational_queue") is True


def test_clinic_plugin_terminology():
    """Plugin clinic expõe terminologia clínica."""
    manifest = plugin_registry.require("clinic")
    assert manifest.term("customer") == "Paciente"
    assert manifest.term("booking") == "Consulta"


def test_marketplace_sports_installable(db, default_company):
    """Sports e clinic aparecem instaláveis no marketplace."""
    listings = MarketplaceService(db).list_listings(default_company.id)
    sports = next(l for l in listings if l["plugin_id"] == "sports")
    clinic = next(l for l in listings if l["plugin_id"] == "clinic")
    assert sports["installable"] is True
    assert sports["available_locally"] is True
    assert clinic["installable"] is True


def test_marketplace_install_sports(db, default_company):
    """POST marketplace install sports altera plugin_id da empresa."""
    company = MarketplaceService(db).install_plugin(default_company.id, "sports")
    assert company.plugin_id == "sports"


def test_production_enforcement_defaults_block(monkeypatch):
    """APP_ENV=production força enforcement block (CF-12)."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert resolve_enforcement_mode() == "block"


def test_production_enforcement_explicit_off(monkeypatch):
    """CORE_ENFORCEMENT_MODE=off desliga mesmo em production."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "off")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert resolve_enforcement_mode() == "off"
