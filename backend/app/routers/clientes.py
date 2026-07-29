"""
Router de Clientes
Endpoints para gerenciamento de clientes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import get_current_active_user, security
from app.modules.identity.api.deps import get_tenant_context, get_identity_service
from app.modules.identity.application.identity_service import IdentityApplicationService
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.services.cliente_service import ClienteService
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _has_effective_company(
    identity: IdentityApplicationService,
    user: User,
    credentials: HTTPAuthorizationCredentials,
) -> bool:
    """
    Indica se o usuário possui tenant efetivo (JWT ``company_id`` ou membership).

    Evita que o fallback para ``salao-demo`` exponha listagens globais a
    usuários sem vínculo de empresa.

    Args:
        identity: Serviço Identity.
        user: Usuário autenticado.
        credentials: Bearer token da requisição.

    Returns:
        True se há ``company_id`` no JWT ou membership primário.
    """
    payload = identity.tokens.decode(credentials.credentials) or {}
    if payload.get("company_id"):
        return True
    return identity.get_primary_membership(user.id) is not None


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
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Lista clientes do tenant ativo — requer autenticação.

    Isolamento: ``Cliente.company_id == tenant.company_id`` (query SQL).
    Usuário sem ``company_id`` efetivo recebe lista vazia.
    """
    if not _has_effective_company(identity, current_user, credentials):
        return []
    service = ClienteService(db)
    return service.listar_clientes(tenant.company_id)


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

