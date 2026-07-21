"""
Router de Reservas (Reservation) — leituras apenas (R3-F3).

Escritas removidas: use ``/v1/bookings`` (RFC-003 M5 / ADR-033).
"""
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin
from app.core.tenant import TenantContext
from app.db.session import get_db
from app.models.agendamento import ReservationStatus
from app.schemas.reservation import ReservationResponse
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["Reservas"])


def _to_response(svc: ReservationService, ag) -> ReservationResponse:
    """
    Converte Agendamento em ReservationResponse enriquecido.

    Args:
        svc: ReservationService com helper de enriquecimento.
        ag: Instância Agendamento.

    Returns:
        ReservationResponse.
    """
    data = svc._enriquecer(ag)
    return ReservationResponse(**data)


@router.get("", response_model=List[ReservationResponse])
def listar_reservas(
    status_filter: Optional[ReservationStatus] = Query(None, alias="status"),
    cliente_id: Optional[int] = Query(None),
    data: Optional[date] = Query(None),
    pendentes: bool = Query(
        False,
        description="Se true, retorna reservas que exigem ação da profissional",
    ),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """
    Lista reservas com filtros (admin) — somente leitura.

    Args:
        status_filter: Filtro de status.
        cliente_id: Filtro por cliente.
        data: Filtro por data.
        pendentes: Se true, apenas pendentes de ação.
        db: Sessão SQLAlchemy.
        tenant: Contexto do tenant admin.

    Returns:
        Lista de ReservationResponse.
    """
    svc = ReservationService(db)
    dt = datetime.combine(data, datetime.min.time()) if data else None
    items = svc.listar(
        status=status_filter,
        cliente_id=cliente_id,
        data_ref=dt,
        pendentes=pendentes,
        company_id=tenant.company_id,
    )
    return [_to_response(svc, ag) for ag in items]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def obter_reserva(reservation_id: int, db: Session = Depends(get_db)):
    """
    Detalhe de uma reserva — somente leitura.

    Args:
        reservation_id: ID do agendamento legado.
        db: Sessão SQLAlchemy.

    Returns:
        ReservationResponse.

    Raises:
        HTTPException: 404 se não encontrado.
    """
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.obter(reservation_id))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
