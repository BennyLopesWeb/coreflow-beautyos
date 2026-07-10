"""
Router API v1 — Assets (metamodelo CoreFlow).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.asset.application.asset_query_service import AssetQueryService
from app.modules.asset.application.legacy_sync_service import AssetLegacySyncService
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.schemas.coreflow_v1 import AssetResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/assets", tags=["CoreFlow — Asset"])


@router.get("", response_model=List[AssetResponse])
def listar_assets(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista ativos/insumos genéricos do tenant.

    Returns:
        Lista de core_assets sincronizados.
    """
    AssetLegacySyncService(db).sync_all()
    return AssetQueryService(db).list_assets(tenant.company_id)


@router.get("/{asset_id}", response_model=AssetResponse)
def obter_asset(
    asset_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de um ativo genérico.

    Args:
        asset_id: ID core_assets.

    Returns:
        AssetResponse.
    """
    try:
        return AssetQueryService(db).get_asset(asset_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
