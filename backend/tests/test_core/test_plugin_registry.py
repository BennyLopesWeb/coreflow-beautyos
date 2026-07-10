"""Testes Plugin Registry — CoreFlow Sprint 0."""
import pytest

from app.core.plugin.registry import PluginRegistry, PLUGINS_DIR
from app.core.plugin.manifest import PluginManifest


def test_plugins_dir_exists():
    """Diretório backend/plugins existe."""
    assert PLUGINS_DIR.is_dir()


def test_load_beauty_plugin():
    """Carrega manifest beauty."""
    registry = PluginRegistry()
    count = registry.load_all()
    assert count >= 1
    beauty = registry.get("beauty")
    assert beauty is not None
    assert beauty.product_name == "BeautyOS"
    assert beauty.has_feature("deposit_payment")
    assert beauty.term("offering") == "Modelo"


def test_plugin_manifest_validation():
    """PluginManifest valida estrutura mínima."""
    manifest = PluginManifest(
        plugin_id="test",
        name="Test Plugin",
        terminology={"booking": "Reserva"},
    )
    assert manifest.term("booking") == "Reserva"
    assert manifest.term("unknown", "Fallback") == "Fallback"


def test_list_plugins_api(client):
    """GET /v1/plugins retorna beauty."""
    from app.core.plugin.registry import plugin_registry
    plugin_registry.load_all()

    response = client.get("/v1/plugins")
    assert response.status_code == 200
    data = response.json()
    assert any(p["plugin_id"] == "beauty" for p in data)


def test_company_plugin_config_api(client, default_company):
    """GET config by company slug retorna terminologia."""
    from app.core.plugin.registry import plugin_registry
    plugin_registry.load_all()

    response = client.get(f"/v1/plugins/config/by-company/{default_company.slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["plugin_id"] == "beauty"
    assert body["product_name"] == "BeautyOS"
    assert "offering" in body["terminology"]
