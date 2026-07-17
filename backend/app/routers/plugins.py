"""
Router de Plugins CoreFlow Platform — API v1.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.plugin.registry import plugin_registry
from app.core.plugin.manifest import PluginManifest
from app.schemas.plugin import PluginManifestResponse, CompanyPluginConfigResponse
from app.modules.identity.api.deps import get_identity_service
from app.modules.identity.application.identity_service import IdentityApplicationService

router = APIRouter(prefix="/v1/plugins", tags=["CoreFlow — Plugins"])


def _to_response(manifest: PluginManifest) -> PluginManifestResponse:
    """
    Converte PluginManifest em DTO de resposta.

    Args:
        manifest: Manifesto carregado.

    Returns:
        PluginManifestResponse serializável.
    """
    return PluginManifestResponse(
        plugin_id=manifest.plugin_id,
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        product_name=manifest.product_name,
        terminology=manifest.terminology,
        features=manifest.features,
        segments=manifest.segments,
        ui=manifest.ui,
        api_version=manifest.api_version,
        hooks=manifest.hook_handler_map(),
        ai_capabilities=manifest.ai_capabilities,
        dependencies=manifest.dependencies,
        sdk=manifest.sdk,
    )


@router.get("", response_model=List[PluginManifestResponse])
def listar_plugins():
    """
    Lista todos os plugins registrados na plataforma CoreFlow.

    Returns:
        Lista de manifests disponíveis.
    """
    manifests = plugin_registry.list_all()
    for manifest in manifests:
        ArchitectureMetricsStore.get().record_plugin_access(manifest.plugin_id)
    return [_to_response(p) for p in manifests]


@router.get("/{plugin_id}", response_model=PluginManifestResponse)
def obter_plugin(plugin_id: str):
    """
    Obtém manifest de um plugin específico.

    Args:
        plugin_id: Identificador (ex.: beauty).

    Returns:
        Manifest do plugin.
    """
    manifest = plugin_registry.get(plugin_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' não encontrado")
    ArchitectureMetricsStore.get().record_plugin_access(plugin_id)
    return _to_response(manifest)


@router.get("/config/by-company/{slug}", response_model=CompanyPluginConfigResponse)
def obter_config_por_empresa(
    slug: str,
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Resolve terminologia e features do plugin ativo de uma empresa.

    Usado por frontends para renderizar rótulos corretos (Build Once. Configure Everywhere).

    Args:
        slug: Slug da empresa.

    Returns:
        Configuração de plugin para o tenant.
    """
    try:
        company = identity.get_company_by_slug(slug)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    plugin_id = company.plugin_id or "beauty"
    try:
        manifest = plugin_registry.require(plugin_id)
    except KeyError:
        raise HTTPException(status_code=500, detail=f"Plugin '{plugin_id}' não registrado")

    from app.modules.push.application.deep_link_service import DeepLinkService

    return CompanyPluginConfigResponse(
        company_id=company.id,
        company_slug=company.slug,
        plugin_id=manifest.plugin_id,
        product_name=manifest.product_name or manifest.name,
        terminology=manifest.terminology,
        features=manifest.features,
        deep_links=DeepLinkService().resolve_config(manifest.plugin_id),
    )
