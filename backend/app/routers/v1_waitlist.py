"""
Router API v1 — Waitlist (metamodelo CoreFlow).
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.waitlist.application.legacy_sync_service import WaitlistLegacySyncService
from app.modules.waitlist.application.waitlist_query_service import WaitlistQueryService
from app.modules.waitlist.domain.models import CoreWaitlistStatus
from app.schemas.coreflow_v1 import WaitlistResponse
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/waitlist", tags=["CoreFlow — Waitlist"])


@router.get("", response_model=List[WaitlistResponse])
def listar_waitlist(
    preferred_date: Optional[date] = Query(None, description="Filtra por data desejada"),
    status: Optional[CoreWaitlistStatus] = Query(None, description="Filtra por status"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista itens da fila de espera genérica do tenant.

    Args:
        preferred_date: Data desejada opcional.
        status: Status opcional (waiting, contacted, etc.).

    Returns:
        Lista de core_waitlist sincronizados da fila legada.
    """
    WaitlistLegacySyncService(db).sync_all()
    return WaitlistQueryService(db).list_waitlist(
        tenant.company_id,
        preferred_date=preferred_date,
        status=status,
    )


@router.get("/{waitlist_id}", response_model=WaitlistResponse)
def obter_waitlist_item(
    waitlist_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Detalhe de um item da fila de espera genérica.

    Args:
        waitlist_id: ID core_waitlist.

    Returns:
        WaitlistResponse.
    """
    try:
        return WaitlistQueryService(db).get_waitlist_item(
            waitlist_id, tenant.company_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
