"""
Schemas de Plugin CoreFlow Platform.
"""
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PluginManifestResponse(BaseModel):
    """
    Resposta pública do manifest de um plugin.

    Attributes:
        plugin_id: ID único do plugin.
        name: Nome do plugin/produto.
        version: Versão do manifest.
        description: Descrição.
        product_name: Nome comercial.
        terminology: Rótulos por conceito do metamodelo.
        features: Capacidades habilitadas.
        segments: Segmentos suportados.
        ui: Configurações de UI.
    """

    plugin_id: str
    name: str
    version: str
    description: str
    product_name: str
    terminology: Dict[str, str]
    features: List[str]
    segments: List[str]
    ui: Dict[str, Any]
    api_version: str = "1"
    hooks: Dict[str, str] = Field(default_factory=dict)
    ai_capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    sdk: Dict[str, Any] = Field(default_factory=dict)


class CompanyPluginConfigResponse(BaseModel):
    """
    Configuração de plugin resolvida para uma empresa.

    Attributes:
        company_id: ID da empresa.
        company_slug: Slug público.
        plugin_id: Plugin ativo.
        product_name: Nome do produto (ex.: BeautyOS).
        terminology: Rótulos UI para o tenant.
        features: Features do plugin.
        deep_links: Configuração de deep links mobile (scheme, routes).
    """

    company_id: int
    company_slug: str
    plugin_id: str
    product_name: str
    terminology: Dict[str, str]
    features: List[str]
    deep_links: Dict[str, Any] = Field(default_factory=dict)
