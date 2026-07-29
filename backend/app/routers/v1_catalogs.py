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

    Quote de entrada mínima usa a política vigente do tenant autenticado
    (nunca ``company_id`` arbitrário do cliente).

    Args:
        catalog_id: ID core_catalogs.

    Returns:
        Lista de offerings ativos.
    """
    from app.modules.booking.domain.policy.activation import (
        calculate_minimum_activation_cents,
        cents_to_decimal,
        money_to_cents,
    )
    from app.modules.booking.domain.policy.resolver import BookingPolicyResolver

    try:
        if tenant.company_id is None:
            raise HTTPException(status_code=403, detail="Tenant não associado")
        rows = CatalogQueryService(db).list_offerings(
            catalog_id, tenant.company_id, active_only=True
        )
        policy = BookingPolicyResolver(db).resolve(int(tenant.company_id))
        result = []
        for row in rows:
            dto = OfferingResponse.model_validate(row)
            total = money_to_cents(row.price_total)
            if total is not None and total > 0:
                minimum = calculate_minimum_activation_cents(
                    total, activation=policy.activation
                )
                dto = dto.model_copy(
                    update={
                        "minimum_activation_cents": minimum,
                        "minimum_activation_amount": cents_to_decimal(minimum),
                    }
                )
            result.append(dto)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
