"""
Router API v1 — Customers (metamodelo CoreFlow).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.customer.application.customer_query_service import CustomerQueryService
from app.modules.customer.application.legacy_sync_service import CustomerLegacySyncService
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.schemas.coreflow_v1 import CustomerResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/customers", tags=["CoreFlow — Customer"])


@router.get("", response_model=List[CustomerResponse])
def listar_customers(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista customers genéricos do tenant (metamodelo Customer).

    Returns:
        Lista de core_customers sincronizados.
    """
    CustomerLegacySyncService(db).sync_all()
    return CustomerQueryService(db).list_customers(tenant.company_id)


@router.get("/{customer_id}", response_model=CustomerResponse)
def obter_customer(
    customer_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de um customer genérico.

    Args:
        customer_id: ID core_customers.

    Returns:
        CustomerResponse.
    """
    try:
        return CustomerQueryService(db).get_customer(customer_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
