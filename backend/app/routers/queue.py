"""
Router da fila operacional (QueueEntry).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from app.db.session import get_db
from app.core.dependencies import get_current_admin_user as get_current_admin
from app.models.user import User
from app.schemas.queue_entry import QueueJoinRequest, QueueEntryResponse, QueueResumoResponse
from app.services.queue_entry_service import QueueEntryService

router = APIRouter(prefix="/queue", tags=["Fila Operacional"])


@router.post("/join", response_model=QueueEntryResponse, status_code=status.HTTP_201_CREATED)
def entrar_fila(dados: QueueJoinRequest, db: Session = Depends(get_db)):
    """Entrar na fila agora (atendimento urgente / mesmo dia)."""
    svc = QueueEntryService(db)
    try:
        entry = svc.entrar(dados)
        return svc._enriquecer(entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=QueueResumoResponse)
def listar_fila(
    data: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista fila operacional do dia (FIFO)."""
    svc = QueueEntryService(db)
    data_ref = data or date.today()
    entries = svc.listar(data_ref)
    return QueueResumoResponse(data=data_ref, total=len(entries), entries=entries)


@router.post("/process-daily")
def processar_fila_diaria(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Rotina: reservas APPROVED de hoje → IN_QUEUE."""
    count = QueueEntryService(db).processar_reservas_do_dia()
    return {"processadas": count}


@router.put("/{entry_id}/call", response_model=QueueEntryResponse)
def chamar_cliente(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Chamar cliente (CALLED)."""
    svc = QueueEntryService(db)
    try:
        return svc._enriquecer(svc.chamar(entry_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}/checkin", response_model=QueueEntryResponse)
def checkin_cliente(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Check-in do cliente."""
    svc = QueueEntryService(db)
    try:
        return svc._enriquecer(svc.checkin(entry_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}/start", response_model=QueueEntryResponse)
def iniciar_atendimento(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Iniciar atendimento (IN_SERVICE)."""
    svc = QueueEntryService(db)
    try:
        return svc._enriquecer(svc.iniciar(entry_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}/complete", response_model=QueueEntryResponse)
def concluir_atendimento(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Finalizar atendimento."""
    svc = QueueEntryService(db)
    try:
        return svc._enriquecer(svc.concluir(entry_id))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}/approve", response_model=QueueEntryResponse)
def aprovar_fila_com_horario(
    entry_id: int,
    data_hora: datetime = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Aprovar entrada urgente criando reserva."""
    svc = QueueEntryService(db)
    try:
        return svc._enriquecer(svc.aprovar_com_horario(entry_id, data_hora))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
