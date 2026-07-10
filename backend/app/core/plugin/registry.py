"""
Plugin Registry — carrega e resolve plugins CoreFlow Platform.
"""
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.core.plugin.manifest import PluginManifest
from app.core.logging_config import get_logger

logger = get_logger("plugin_registry")

# backend/plugins/ (irmão de backend/app/)
PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"


class PluginRegistry:
    """
    Registro central de plugins disponíveis na plataforma.

    Carrega manifests YAML de ``backend/plugins/*/manifest.yaml`` na inicialização.
    Singleton via ``plugin_registry`` global.

    Attributes:
        _plugins: Mapa plugin_id → PluginManifest.
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Inicializa registry vazio.

        Args:
            plugins_dir: Diretório raiz de plugins (default backend/plugins).
        """
        self._plugins_dir = plugins_dir or PLUGINS_DIR
        self._plugins: Dict[str, PluginManifest] = {}

    def load_all(self) -> int:
        """
        Escaneia diretório de plugins e carrega todos os manifests.

        Returns:
            Quantidade de plugins carregados.
        """
        self._plugins.clear()
        if not self._plugins_dir.is_dir():
            logger.warning(f"Diretório de plugins não encontrado: {self._plugins_dir}")
            return 0

        count = 0
        for manifest_path in sorted(self._plugins_dir.glob("*/manifest.yaml")):
            try:
                manifest = self._load_file(manifest_path)
                self._plugins[manifest.plugin_id] = manifest
                count += 1
                logger.info(f"Plugin carregado: {manifest.plugin_id} ({manifest.name})")
            except Exception as exc:
                logger.error(f"Erro ao carregar {manifest_path}: {exc}")
        return count

    def _load_file(self, path: Path) -> PluginManifest:
        """
        Carrega um manifest YAML do disco.

        Args:
            path: Caminho do arquivo manifest.yaml.

        Returns:
            PluginManifest validado.
        """
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        return PluginManifest(**data)

    def get(self, plugin_id: str) -> Optional[PluginManifest]:
        """
        Obtém plugin por ID.

        Args:
            plugin_id: Identificador do plugin.

        Returns:
            PluginManifest ou None.
        """
        return self._plugins.get(plugin_id)

    def require(self, plugin_id: str) -> PluginManifest:
        """
        Obtém plugin ou lança KeyError.

        Args:
            plugin_id: Identificador do plugin.

        Returns:
            PluginManifest.

        Raises:
            KeyError: Se plugin não registrado.
        """
        manifest = self.get(plugin_id)
        if not manifest:
            raise KeyError(f"Plugin não encontrado: {plugin_id}")
        return manifest

    def list_all(self) -> List[PluginManifest]:
        """
        Lista todos os plugins registrados.

        Returns:
            Lista ordenada por plugin_id.
        """
        return sorted(self._plugins.values(), key=lambda p: p.plugin_id)

    def resolve_for_company(self, plugin_id: str) -> PluginManifest:
        """
        Resolve manifest para uma empresa (tenant).

        Args:
            plugin_id: plugin_id da Company.

        Returns:
            PluginManifest correspondente.

        Raises:
            KeyError: Se plugin_id inválido.
        """
        return self.require(plugin_id)


plugin_registry = PluginRegistry()
