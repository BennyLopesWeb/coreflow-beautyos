"""
Modelo de manifest de plugin CoreFlow Platform.
"""
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field


class HookBinding(BaseModel):
    """
    Binding tipado de hook no manifest (ADR-011).

    Args:
        handler: Path Python sob ``app.plugins.*``.
        async_mode: Preferência async (campo YAML ``async``).
    """

    handler: str
    async_mode: bool = Field(default=False, alias="async")

    model_config = {"populate_by_name": True}


class PluginManifest(BaseModel):
    """
    Manifesto declarativo de um plugin CoreFlow.

    Define terminologia, features e mapeamento para o metamodelo genérico.
    Carregado de ``backend/plugins/{plugin_id}/manifest.yaml``.

    Attributes:
        plugin_id: Identificador único (ex.: beauty, sports, clinic).
        name: Nome do produto/plugin.
        version: Versão semver do manifest.
        description: Descrição curta.
        product_name: Nome comercial exibido ao usuário final.
        terminology: Rótulos UI por conceito do metamodelo.
        features: Flags de capacidades habilitadas.
        segments: Segmentos de mercado suportados.
        metamodel_mappings: Entidades legado/core mapeadas.
        ui: Configurações de interface específicas do plugin.
        hooks: Mapa hook → path str ou HookBinding (ADR-011).
        agents: Declaração de agents do plugin (ex.: beauty-assistant).
    """

    plugin_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    product_name: str = ""
    terminology: Dict[str, str] = Field(default_factory=dict)
    features: List[str] = Field(default_factory=list)
    segments: List[str] = Field(default_factory=list)
    metamodel_mappings: Dict[str, str] = Field(default_factory=dict)
    ui: Dict[str, Any] = Field(default_factory=dict)
    api_version: str = "1"
    hooks: Dict[str, Union[str, Dict[str, Any], HookBinding]] = Field(
        default_factory=dict
    )
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    ai_capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    sdk: Dict[str, Any] = Field(default_factory=dict)
    mobile: Dict[str, Any] = Field(default_factory=dict)
    resource_types: List[Dict[str, Any]] = Field(default_factory=list)

    def resolve_hook_binding(self, hook_name: str) -> Tuple[Optional[str], bool]:
        """
        Normaliza binding de hook (str legado ou objeto ADR-011).

        Args:
            hook_name: Nome do hook.

        Returns:
            Tupla (handler_path, async_mode). path None se ausente/inválido.
        """
        raw = self.hooks.get(hook_name)
        if raw is None:
            return None, False
        if isinstance(raw, str):
            return raw, False
        if isinstance(raw, HookBinding):
            return raw.handler, raw.async_mode
        if isinstance(raw, dict):
            handler = raw.get("handler")
            if not handler:
                return None, False
            return str(handler), bool(raw.get("async", False))
        return None, False

    def hook_handler_map(self) -> Dict[str, str]:
        """
        Mapa plano hook → handler path (para API/response compatível).

        Returns:
            Dict[str, str] apenas com paths resolvidos.
        """
        result: Dict[str, str] = {}
        for name in self.hooks:
            path, _ = self.resolve_hook_binding(name)
            if path:
                result[name] = path
        return result


    def has_feature(self, feature: str) -> bool:
        """
        Verifica se o plugin declara uma feature.

        Args:
            feature: Nome da feature (ex.: deposit_payment).

        Returns:
            True se a feature está listada.
        """
        return feature in self.features

    def has_ai_capability(self, capability: str) -> bool:
        """
        Verifica se o plugin declara uma capacidade IA.

        Args:
            capability: Nome da capacidade (ex.: crm_followup).

        Returns:
            True se a capacidade está listada em ai_capabilities.
        """
        return capability in self.ai_capabilities

    def term(self, concept: str, default: Optional[str] = None) -> str:
        """
        Retorna rótulo de terminologia para um conceito do metamodelo.

        Args:
            concept: Chave do conceito (ex.: booking, worker).
            default: Fallback se não definido no manifest.

        Returns:
            Rótulo traduzido/configurado.
        """
        return self.terminology.get(concept, default or concept.capitalize())
