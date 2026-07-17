"""
ResourceTypePort — tipos declarados no plugin manifest (R2-F3).
"""
from typing import Any, Dict, Optional, Protocol


class ResourceTypePort(Protocol):
    """
    Port para resolver resource_types do plugin.
    """

    def resolve(
        self, plugin_id: str, type_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve declaração de tipo no manifest.

        Args:
            plugin_id: Plugin (ex.: beauty).
            type_id: ID do tipo (ex.: chair).

        Returns:
            Dict com id, label, default_capacity — ou None se desconhecido.
        """
        ...
