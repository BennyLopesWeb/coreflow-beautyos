"""
Router de Financeiro
Endpoints para gerenciamento financeiro
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.financeiro import SaidaCreate, ResumoFinanceiroResponse
from app.services.financeiro_service import FinanceiroService

router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


@router.get("/resumo", response_model=ResumoFinanceiroResponse)
def obter_resumo_financeiro(
    inicio: datetime = Query(..., description="Data inicial do período"),
    fim: datetime = Query(..., description="Data final do período"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtém resumo financeiro do período
    Retorna totais de entradas, saídas e saldo
    Requer autenticação
    """
    service = FinanceiroService(db)
    try:
        return service.obter_resumo(inicio, fim)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/saida", status_code=status.HTTP_201_CREATED)
def registrar_saida(
    saida_data: SaidaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Registra saída financeira manual
    Valida valor antes de registrar
    Requer autenticação
    """
    service = FinanceiroService(db)
    try:
        return service.registrar_saida(saida_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

