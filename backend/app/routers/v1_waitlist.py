"""
Router API v1 — Waitlist (metamodelo CoreFlow).
"""
from datetime import date
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.modules.waitlist.application.commands.promote_waitlist import (
    PromoteWaitlistCommand,
    PromoteWaitlistHandler,
)
from app.modules.waitlist.application.legacy_sync_service import WaitlistLegacySyncService
from app.modules.waitlist.application.waitlist_query_service import WaitlistQueryService
from app.modules.waitlist.domain.models import CoreWaitlistStatus
from app.schemas.coreflow_v1 import (
    WaitlistPromoteRequest,
    WaitlistPromoteResponse,
    WaitlistResponse,
)
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


@router.post("/{waitlist_id}/promote", response_model=WaitlistPromoteResponse)
def promover_waitlist(
    waitlist_id: int,
    body: WaitlistPromoteRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Promove item da fila para booking e dispara hook ``waitlist.promoted`` (P10).

    Args:
        waitlist_id: ID ``core_waitlist``.
        body: Horário confirmado e notes opcionais.
        request: Request HTTP (correlation).
        tenant: Tenant autenticado.
        db: Sessão.
        _: Admin autenticado.

    Returns:
        WaitlistPromoteResponse com booking_id e contagem de hooks.

    Raises:
        HTTPException: 404/409/400 conforme domínio.
    """
    correlation = request.headers.get("X-Correlation-Id") or str(uuid4())
    try:
        result = PromoteWaitlistHandler(db).execute(
            PromoteWaitlistCommand(
                waitlist_id=waitlist_id,
                company_id=tenant.company_id,
                scheduled_at=body.scheduled_at,
                notes=body.notes,
                correlation_id=correlation,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return WaitlistPromoteResponse(
        waitlist=WaitlistResponse.model_validate(result.waitlist),
        booking_id=result.booking_id,
        hook_dispatched=result.hook_dispatched,
    )
