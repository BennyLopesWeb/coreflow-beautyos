"""
Router API v1 — Inventory (metamodelo CoreFlow).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.asset.application.legacy_sync_service import AssetLegacySyncService
from app.modules.inventory.inventory_service import InventoryService
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.schemas.coreflow_v1 import InventoryResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/inventory", tags=["CoreFlow — Inventory"])


@router.get("", response_model=List[InventoryResponse])
def listar_inventory(
    asset_id: Optional[int] = Query(None, description="Filtra por core_assets"),
    low_stock_only: bool = Query(False, description="Apenas estoque baixo"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista níveis de estoque genéricos do tenant.

    Returns:
        Lista de core_inventory sincronizados.
    """
    AssetLegacySyncService(db).sync_all()
    return InventoryService(db).list_inventory(
        tenant.company_id,
        asset_id=asset_id,
        low_stock_only=low_stock_only,
    )


@router.get("/{inventory_id}", response_model=InventoryResponse)
def obter_inventory(
    inventory_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de um registro de estoque.

    Args:
        inventory_id: ID core_inventory.

    Returns:
        InventoryResponse.
    """
    try:
        return InventoryService(db).get_inventory(inventory_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
