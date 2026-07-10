"""
Router API v1 — Orders (metamodelo CoreFlow).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.order.application.legacy_sync_service import OrderLegacySyncService
from app.modules.order.application.order_query_service import OrderQueryService
from app.schemas.coreflow_v1 import OrderResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/orders", tags=["CoreFlow — Order"])


@router.get("", response_model=List[OrderResponse])
def listar_orders(
    booking_id: Optional[int] = Query(None, description="Filtra por core_bookings"),
    customer_id: Optional[int] = Query(None, description="Filtra por cliente legado"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista pedidos comerciais genéricos do tenant.

    Returns:
        Lista de core_orders sincronizados.
    """
    OrderLegacySyncService(db).sync_all()
    return OrderQueryService(db).list_orders(
        tenant.company_id,
        booking_id=booking_id,
        customer_id=customer_id,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def obter_order(
    order_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de um pedido genérico.

    Args:
        order_id: ID core_orders.

    Returns:
        OrderResponse.
    """
    try:
        return OrderQueryService(db).get_order(order_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
