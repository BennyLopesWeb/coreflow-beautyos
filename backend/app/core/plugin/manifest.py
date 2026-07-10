"""
Modelo de manifest de plugin CoreFlow Platform.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    hooks: Dict[str, str] = Field(default_factory=dict)
    ai_capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    sdk: Dict[str, Any] = Field(default_factory=dict)
    mobile: Dict[str, Any] = Field(default_factory=dict)

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
