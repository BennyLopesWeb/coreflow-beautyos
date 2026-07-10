"""
CoreFlow Plugin System — Plugin First architecture.
"""
from app.core.plugin.manifest import PluginManifest
from app.core.plugin.registry import PluginRegistry, plugin_registry, PLUGINS_DIR

__all__ = ["PluginManifest", "PluginRegistry", "plugin_registry", "PLUGINS_DIR"]
