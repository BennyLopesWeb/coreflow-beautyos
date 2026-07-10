"""
Router API v1 — Catalog (metamodelo CoreFlow).
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_db
from sqlalchemy.orm import Session

from app.modules.identity.api.deps import get_tenant_context
from app.shared.kernel.tenant import TenantContext
from app.modules.catalog.application.catalog_query_service import CatalogQueryService
from app.schemas.coreflow_v1 import CatalogResponse, OfferingResponse

router = APIRouter(prefix="/v1/catalogs", tags=["CoreFlow — Catalog"])


@router.get("", response_model=List[CatalogResponse])
def listar_catalogos(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lista catálogos genéricos do tenant (metamodelo Catalog).

    No plugin beauty, equivalente a GET /trancas com nomenclatura CoreFlow.

    Returns:
        Lista de catálogos ativos.
    """
    svc = CatalogQueryService(db)
    return svc.list_catalogs(tenant.company_id, active_only=True)


@router.get("/{catalog_id}", response_model=CatalogResponse)
def obter_catalogo(
    catalog_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de um catálogo genérico.

    Args:
        catalog_id: ID core_catalogs.

    Returns:
        CatalogResponse.
    """
    try:
        return CatalogQueryService(db).get_catalog(catalog_id, tenant.company_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{catalog_id}/offerings", response_model=List[OfferingResponse])
def listar_offerings(
    catalog_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lista offerings (variantes comerciais) de um catálogo.

    Args:
        catalog_id: ID core_catalogs.

    Returns:
        Lista de offerings ativos.
    """
    try:
        return CatalogQueryService(db).list_offerings(
            catalog_id, tenant.company_id, active_only=True
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
