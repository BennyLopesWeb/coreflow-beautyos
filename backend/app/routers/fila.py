"""
Router de Fila de Espera
Endpoints para entrada e consulta da fila virtual.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from app.db.session import get_db
from app.core.dependencies import get_current_admin_user as get_current_admin
from app.models.user import User
from app.schemas.fila import (
    FilaEsperaCreate,
    FilaResponse,
    FilaResumoResponse,
    FilaAtualizarStatusRequest,
    FilaAprovarRequest,
)
from app.services.fila_service import FilaService

router = APIRouter(prefix="/fila", tags=["Fila de Espera"])


@router.post("/entrar", response_model=FilaResponse, status_code=status.HTTP_201_CREATED)
def entrar_na_fila(
    dados: FilaEsperaCreate,
    db: Session = Depends(get_db),
):
    """
    Cliente entra na fila de espera sem horário confirmado.
    """
    service = FilaService(db)
    try:
        return service.entrar_na_fila(dados)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{data_ref}", response_model=FilaResumoResponse)
def consultar_fila(
    data_ref: date,
    db: Session = Depends(get_db),
):
    """
    Consulta fila de uma data (FIFO).
    """
    service = FilaService(db)
    filas = service.consultar_fila_detalhada(data_ref)
    return FilaResumoResponse(data=data_ref, total_pessoas=len(filas), posicoes=filas)


@router.get("/posicao/{cliente_id}/{data_ref}")
def consultar_posicao(
    cliente_id: int,
    data_ref: date,
    db: Session = Depends(get_db),
):
    """
    Retorna posição do cliente na fila do dia.
    """
    posicao = FilaService(db).obter_posicao_cliente(cliente_id, data_ref)
    return {"cliente_id": cliente_id, "data": data_ref.isoformat(), "posicao": posicao}


@router.patch("/admin/{fila_id}/status", response_model=FilaResponse)
def atualizar_status_fila(
    fila_id: int,
    body: FilaAtualizarStatusRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin marca item como contactado ou outro status."""
    try:
        return FilaService(db).atualizar_status(fila_id, body.status)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin/{fila_id}/aprovar", response_model=FilaResponse)
def aprovar_fila(
    fila_id: int,
    body: FilaAprovarRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin aprova fila, cria reserva e solicita pagamento."""
    try:
        return FilaService(db).aprovar_fila(fila_id, body)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin/{fila_id}/rejeitar", response_model=FilaResponse)
def rejeitar_fila(
    fila_id: int,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin rejeita solicitação da fila."""
    try:
        return FilaService(db).rejeitar_fila(fila_id, motivo)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/admin/{fila_id}", response_model=FilaResponse)
def cancelar_fila(
    fila_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin cancela item da fila."""
    try:
        return FilaService(db).cancelar_fila(fila_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
