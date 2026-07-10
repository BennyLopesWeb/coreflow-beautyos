"""
Router de empresas (tenant) — módulo Identity (API adapter).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse
from app.modules.identity.api.deps import (
    get_identity_service,
    get_current_platform_admin,
)
from app.modules.identity.application.identity_service import IdentityApplicationService

router = APIRouter(prefix="/companies", tags=["Empresas"])


@router.get("", response_model=List[CompanyResponse])
def listar_empresas(
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Lista empresas ativas (público).

    Returns:
        Lista de empresas.
    """
    return identity.list_active_companies()


@router.get("/{slug}", response_model=CompanyResponse)
def obter_empresa(
    slug: str,
    identity: IdentityApplicationService = Depends(get_identity_service),
):
    """
    Obtém empresa pelo slug público.

    Args:
        slug: Identificador URL.

    Returns:
        CompanyResponse.
    """
    try:
        return identity.get_company_by_slug(slug)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def criar_empresa(
    dados: CompanyCreate,
    identity: IdentityApplicationService = Depends(get_identity_service),
    _: User = Depends(get_current_platform_admin),
):
    """
    Cria nova empresa (superuser da plataforma).

    Returns:
        Empresa criada.
    """
    try:
        return identity.create_company(dados)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
