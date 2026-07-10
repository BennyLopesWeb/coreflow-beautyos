"""
Router API v1 — Payments (metamodelo CoreFlow).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.payments.application.legacy_sync_service import PaymentLegacySyncService
from app.modules.payments.application.payment_query_service import PaymentQueryService
from app.schemas.coreflow_v1 import PaymentResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/payments", tags=["CoreFlow — Payment"])


@router.get("", response_model=List[PaymentResponse])
def listar_payments(
    booking_id: Optional[int] = Query(None, description="ID core_bookings"),
    legacy_agendamento_id: Optional[int] = Query(None, description="ID agendamentos legado"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista pagamentos genéricos do tenant.

    Args:
        booking_id: Filtra por booking core.
        legacy_agendamento_id: Filtra por agendamento legado.

    Returns:
        Lista de core_payments.
    """
    PaymentLegacySyncService(db).sync_all()
    svc = PaymentQueryService(db)
    if booking_id is not None:
        return svc.list_by_booking(booking_id, tenant.company_id)
    if legacy_agendamento_id is not None:
        return svc.list_by_legacy_agendamento(
            legacy_agendamento_id, tenant.company_id
        )
    raise HTTPException(
        status_code=400,
        detail="Informe booking_id ou legacy_agendamento_id",
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def obter_payment(
    payment_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de um pagamento genérico.

    Args:
        payment_id: ID core_payments.

    Returns:
        PaymentResponse.
    """
    try:
        return PaymentQueryService(db).get_payment(payment_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
