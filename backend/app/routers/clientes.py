"""
Router de Clientes
Endpoints para gerenciamento de clientes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.post("", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def criar_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cria novo cliente
    Valida telefone único
    Requer autenticação
    """
    service = ClienteService(db)
    try:
        return service.criar_cliente(cliente_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[ClienteResponse])
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os clientes - requer autenticação"""
    service = ClienteService(db)
    return service.listar_clientes()


@router.get("/por-telefone/{telefone}", response_model=ClienteResponse)
def buscar_por_telefone(
    telefone: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Busca cliente pelo telefone exato.
    Requer autenticação.
    """
    service = ClienteService(db)
    cliente = service.buscar_por_telefone(telefone)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return cliente


@router.get("/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """Obtém detalhes de um cliente"""
    service = ClienteService(db)
    try:
        return service.obter_cliente(cliente_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza cliente existente - requer autenticação"""
    service = ClienteService(db)
    try:
        return service.atualizar_cliente(cliente_id, cliente_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

