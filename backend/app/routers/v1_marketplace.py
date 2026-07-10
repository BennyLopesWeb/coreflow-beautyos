"""
Router API v1 — Marketplace (catálogo cloud proto).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.marketplace.application.marketplace_service import MarketplaceService
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/marketplace", tags=["CoreFlow — Marketplace"])


class MarketplaceListingResponse(BaseModel):
    """
    Entrada do catálogo marketplace.

    Attributes:
        plugin_id: ID do plugin.
        name: Nome.
        version: Versão semver.
        description: Descrição.
        product_name: Nome comercial.
        source: local | marketplace.
        installable: Se pode ser instalado agora.
        pricing: free | freemium | paid.
        min_platform_version: Versão mínima CoreFlow.
        installed: Se é o plugin ativo do tenant.
        available_locally: Se manifest existe no servidor.
        local_version: Versão local se disponível.
    """

    plugin_id: str
    name: str
    version: str
    description: str = ""
    product_name: str = ""
    source: str
    installable: bool
    pricing: str = "free"
    min_platform_version: str = "0.1.0"
    installed: bool = False
    available_locally: bool = False
    local_version: str | None = None


class MarketplaceInstallRequest(BaseModel):
    """Body para instalação de plugin no tenant."""

    plugin_id: str = Field(..., description="ID do plugin a instalar")


class MarketplaceInstallResponse(BaseModel):
    """Resposta após instalação de plugin."""

    company_id: int
    company_slug: str
    plugin_id: str
    message: str


@router.get("/listings", response_model=List[MarketplaceListingResponse])
def listar_marketplace(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista plugins do marketplace cloud + locais.

    Returns:
        Catálogo com flag installed para o tenant atual.
    """
    return MarketplaceService(db).list_listings(tenant.company_id)


@router.post("/install", response_model=MarketplaceInstallResponse)
def instalar_plugin_marketplace(
    body: MarketplaceInstallRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Instala/ativa plugin no tenant (altera company.plugin_id).

    Args:
        body: plugin_id a instalar.

    Returns:
        Confirmação com plugin ativo.
    """
    try:
        company = MarketplaceService(db).install_plugin(
            tenant.company_id, body.plugin_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return MarketplaceInstallResponse(
        company_id=company.id,
        company_slug=company.slug,
        plugin_id=company.plugin_id,
        message=f"Plugin '{body.plugin_id}' ativado com sucesso",
    )
