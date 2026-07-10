"""
Router de Agendamentos
Endpoints para gerenciamento de agendamentos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.agendamento import (
    AgendamentoCreate, AgendamentoUpdate, AgendamentoResponse,
    DisponibilidadeResponse, HorarioDisponivel
)
from app.services.agendamento_service import AgendamentoService
from app.services.disponibilidade_service import DisponibilidadeService
from app.utils.agendamento_response import agendamento_para_response

router = APIRouter(prefix="/agenda", tags=["Agendamentos"])


@router.get("/disponibilidade", response_model=DisponibilidadeResponse)
def consultar_disponibilidade(
    data: datetime = Query(..., description="Data e hora para consulta"),
    tranca_id: int = Query(..., description="ID da trança"),
    service_image_id: int | None = Query(None, description="ID da foto/modelo (duração individual)"),
    db: Session = Depends(get_db)
):
    """
    Consulta horários disponíveis para uma data, trança e modelo opcional.
    """
    service = DisponibilidadeService(db)
    try:
        horarios = service.calcular_horarios_disponiveis(data, tranca_id, service_image_id)
        return DisponibilidadeResponse(
            data=data,
            tranca_id=tranca_id,
            horarios=horarios
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/agendamentos", response_model=AgendamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_agendamento(
    agendamento_data: AgendamentoCreate,
    db: Session = Depends(get_db)
):
    """
    Cria novo agendamento
    Valida disponibilidade antes de criar
    """
    service = AgendamentoService(db)
    try:
        ag = service.criar_agendamento(agendamento_data)
        return agendamento_para_response(ag)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os agendamentos - requer autenticação"""
    service = AgendamentoService(db)
    return [agendamento_para_response(a) for a in service.listar_agendamentos()]


@router.get("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def obter_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhes de um agendamento"""
    service = AgendamentoService(db)
    try:
        return agendamento_para_response(service.obter_agendamento(agendamento_id))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def atualizar_agendamento(
    agendamento_id: int,
    agendamento_data: AgendamentoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza agendamento existente - requer autenticação"""
    service = AgendamentoService(db)
    try:
        return agendamento_para_response(
            service.atualizar_agendamento(agendamento_id, agendamento_data)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/agendamentos/{agendamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancela agendamento - requer autenticação"""
    service = AgendamentoService(db)
    try:
        service.cancelar_agendamento(agendamento_id)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

