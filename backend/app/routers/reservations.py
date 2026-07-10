"""
Router de Reservas (Reservation).
API REST completa do ciclo de reserva.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List, Optional

from app.db.session import get_db
from app.core.dependencies import get_current_admin, get_current_admin_user, get_tenant_context
from app.core.tenant import TenantContext
from app.models.agendamento import ReservationStatus
from app.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationRejectRequest,
    ReservationRescheduleRequest,
    ReservationAcceptRescheduleRequest,
)
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["Reservas"])


def _to_response(svc: ReservationService, ag) -> ReservationResponse:
    """Converte Agendamento em ReservationResponse enriquecido."""
    data = svc._enriquecer(ag)
    return ReservationResponse(**data)


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def criar_reserva(
    dados: ReservationCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    """Cria reserva sobre modelo específico (PENDING_PAYMENT)."""
    svc = ReservationService(db)
    try:
        ag = svc.criar_de_schema(dados, company_id=tenant.company_id)
        return _to_response(svc, ag)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    """Lista reservas com filtros (admin)."""
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
    """Detalhe de uma reserva."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.obter(reservation_id))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{reservation_id}/approve", response_model=ReservationResponse)
def aprovar_reserva(
    reservation_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """Admin aprova reserva → APPROVED."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.aprovar(reservation_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{reservation_id}/reject", response_model=ReservationResponse)
def rejeitar_reserva(
    reservation_id: int,
    body: ReservationRejectRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """Admin rejeita reserva."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.rejeitar(reservation_id, body.motivo))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{reservation_id}/reschedule", response_model=ReservationResponse)
def reagendar_reserva(
    reservation_id: int,
    body: ReservationRescheduleRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """Admin sugere novo horário."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.solicitar_reagendamento(
            reservation_id, body.novo_horario, body.mensagem
        ))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{reservation_id}/accept-reschedule", response_model=ReservationResponse)
def aceitar_reagendamento(
    reservation_id: int,
    body: ReservationAcceptRescheduleRequest,
    db: Session = Depends(get_db),
):
    """Cliente aceita horário sugerido."""
    if not body.aceitar:
        raise HTTPException(status_code=400, detail="Reagendamento recusado")
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.aceitar_reagendamento(reservation_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{reservation_id}/complete", response_model=ReservationResponse)
def concluir_reserva(
    reservation_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_admin),
):
    """Marca atendimento como concluído."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.concluir(reservation_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{reservation_id}", response_model=ReservationResponse)
def cancelar_reserva(
    reservation_id: int,
    motivo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Cancela reserva."""
    svc = ReservationService(db)
    try:
        return _to_response(svc, svc.cancelar(reservation_id, motivo))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
