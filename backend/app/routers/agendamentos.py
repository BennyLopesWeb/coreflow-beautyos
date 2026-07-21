"""
Router de Agendamentos — leituras + disponibilidade (R3-F3).

Escritas ``POST/PUT/DELETE /agenda/agendamentos`` removidas: use ``/v1/bookings``.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.agendamento import AgendamentoResponse, DisponibilidadeResponse
from app.services.agendamento_service import AgendamentoService
from app.services.disponibilidade_service import DisponibilidadeService
from app.utils.agendamento_response import agendamento_para_response

router = APIRouter(prefix="/agenda", tags=["Agendamentos"])


@router.get("/disponibilidade", response_model=DisponibilidadeResponse)
def consultar_disponibilidade(
    data: datetime = Query(..., description="Data e hora para consulta"),
    tranca_id: int = Query(..., description="ID da trança"),
    service_image_id: int | None = Query(None, description="ID da foto/modelo (duração individual)"),
    db: Session = Depends(get_db),
):
    """
    Consulta horários disponíveis para uma data, trança e modelo opcional.

    Args:
        data: Data/hora de referência.
        tranca_id: ID da trança legado.
        service_image_id: ID do modelo opcional.
        db: Sessão SQLAlchemy.

    Returns:
        DisponibilidadeResponse com lista de horários.
    """
    service = DisponibilidadeService(db)
    try:
        horarios = service.calcular_horarios_disponiveis(data, tranca_id, service_image_id)
        return DisponibilidadeResponse(
            data=data,
            tranca_id=tranca_id,
            horarios=horarios,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/agendamentos", response_model=List[AgendamentoResponse])
def listar_agendamentos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lista todos os agendamentos — requer autenticação (somente leitura).

    Args:
        db: Sessão SQLAlchemy.
        current_user: Usuário autenticado.

    Returns:
        Lista de AgendamentoResponse.
    """
    service = AgendamentoService(db)
    return [agendamento_para_response(a) for a in service.listar_agendamentos()]


@router.get("/agendamentos/{agendamento_id}", response_model=AgendamentoResponse)
def obter_agendamento(
    agendamento_id: int,
    db: Session = Depends(get_db),
):
    """
    Obtém detalhes de um agendamento — somente leitura.

    Args:
        agendamento_id: ID do agendamento.
        db: Sessão SQLAlchemy.

    Returns:
        AgendamentoResponse.
    """
    service = AgendamentoService(db)
    try:
        return agendamento_para_response(service.obter_agendamento(agendamento_id))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
