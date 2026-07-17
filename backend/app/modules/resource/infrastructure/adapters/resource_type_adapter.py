"""
PluginResourceTypeAdapter — ResourceTypePort via PluginRegistry (R2-F3).
"""
from typing import Any, Dict, Optional

from app.core.plugin.registry import plugin_registry


class PluginResourceTypeAdapter:
    """
    Resolve resource_types declarados no manifest do plugin.

    Args:
        default_plugin_id: Plugin fallback (beauty).
    """

    def __init__(self, default_plugin_id: str = "beauty"):
        self._default_plugin = default_plugin_id

    def resolve(
        self, plugin_id: str, type_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve tipo no manifest.

        Args:
            plugin_id: Plugin id.
            type_id: Tipo (chair, court, …).

        Returns:
            Dict tipado ou None.
        """
        if not plugin_registry._plugins:
            plugin_registry.load_all()
        plugin = plugin_registry.get(plugin_id) or plugin_registry.get(
            self._default_plugin
        )
        if not plugin:
            # Fallback genérico se registry vazio em testes
            if type_id.lower() in {"chair", "court", "room", "generic"}:
                return {
                    "id": type_id.lower(),
                    "label": type_id.title(),
                    "default_capacity": 1,
                }
            return None
        types = getattr(plugin, "resource_types", None) or []
        needle = type_id.strip().lower()
        for entry in types:
            entry_id = str(entry.get("id", "")).lower()
            if entry_id == needle:
                return {
                    "id": entry_id,
                    "label": entry.get("label", entry_id),
                    "default_capacity": int(entry.get("default_capacity", 1)),
                }
        # Fallback enum CoreFlow conhecido
        if needle in {"chair", "court", "room", "generic", "professional"}:
            return {"id": needle, "label": needle.title(), "default_capacity": 1}
        return None
