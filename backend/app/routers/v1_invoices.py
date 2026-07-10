"""
Router API v1 — Invoices (metamodelo CoreFlow).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.invoice.application.legacy_sync_service import InvoiceLegacySyncService
from app.modules.invoice.application.invoice_query_service import InvoiceQueryService
from app.schemas.coreflow_v1 import InvoiceResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/invoices", tags=["CoreFlow — Invoice"])


@router.get("", response_model=List[InvoiceResponse])
def listar_invoices(
    order_id: Optional[int] = Query(None, description="Filtra por core_orders"),
    booking_id: Optional[int] = Query(None, description="Filtra por core_bookings"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista faturas/recibos genéricos do tenant.

    Returns:
        Lista de core_invoices sincronizados de entradas financeiras.
    """
    InvoiceLegacySyncService(db).sync_all()
    return InvoiceQueryService(db).list_invoices(
        tenant.company_id,
        order_id=order_id,
        booking_id=booking_id,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def obter_invoice(
    invoice_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de uma fatura genérica.

    Args:
        invoice_id: ID core_invoices.

    Returns:
        InvoiceResponse.
    """
    try:
        return InvoiceQueryService(db).get_invoice(invoice_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
