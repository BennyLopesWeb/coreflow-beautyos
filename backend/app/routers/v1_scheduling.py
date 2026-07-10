"""
Routers API v1 — Scheduling (Location, Worker, Resource, Availability).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.session import get_db
from app.modules.identity.api.deps import get_tenant_context
from app.modules.scheduling.application.availability_service import SchedulingAvailabilityService
from app.modules.scheduling.application.scheduling_query_service import SchedulingQueryService
from app.schemas.coreflow_v1 import (
    AvailabilitySlotResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    LocationResponse,
    ResourceResponse,
    WorkerResponse,
)
from app.shared.kernel.tenant import TenantContext

locations_router = APIRouter(prefix="/v1/locations", tags=["CoreFlow — Location"])
workers_router = APIRouter(prefix="/v1/workers", tags=["CoreFlow — Worker"])
resources_router = APIRouter(prefix="/v1/resources", tags=["CoreFlow — Resource"])
scheduling_router = APIRouter(prefix="/v1/scheduling", tags=["CoreFlow — Scheduling"])


@locations_router.get("", response_model=List[LocationResponse])
def listar_locations(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lista unidades físicas do tenant (metamodelo Location).

    Returns:
        Lista de locations ativas.
    """
    return SchedulingQueryService(db).list_locations(tenant.company_id, active_only=True)


@locations_router.get("/{location_id}", response_model=LocationResponse)
def obter_location(
    location_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de uma unidade física.

    Args:
        location_id: ID core_locations.

    Returns:
        LocationResponse.
    """
    try:
        return SchedulingQueryService(db).get_location(location_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@workers_router.get("", response_model=List[WorkerResponse])
def listar_workers(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lista profissionais do tenant (metamodelo Worker).

    Returns:
        Lista de workers ativos.
    """
    return SchedulingQueryService(db).list_workers(tenant.company_id, active_only=True)


@workers_router.get("/{worker_id}", response_model=WorkerResponse)
def obter_worker(
    worker_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de um profissional.

    Args:
        worker_id: ID core_workers.

    Returns:
        WorkerResponse.
    """
    try:
        return SchedulingQueryService(db).get_worker(worker_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@resources_router.get("", response_model=List[ResourceResponse])
def listar_resources(
    location_id: Optional[int] = Query(None, description="Filtrar por unidade"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lista recursos reserváveis do tenant (metamodelo Resource).

    Args:
        location_id: Filtro opcional por location.

    Returns:
        Lista de resources ativos.
    """
    return SchedulingQueryService(db).list_resources(
        tenant.company_id, location_id=location_id, active_only=True
    )


@resources_router.get("/{resource_id}", response_model=ResourceResponse)
def obter_resource(
    resource_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de um recurso reservável.

    Args:
        resource_id: ID core_resources.

    Returns:
        ResourceResponse.
    """
    try:
        return SchedulingQueryService(db).get_resource(resource_id, tenant.company_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@scheduling_router.get("/availability", response_model=List[AvailabilitySlotResponse])
def consultar_disponibilidade(
    date: datetime = Query(..., description="Data base (ISO 8601)"),
    catalog_id: int = Query(..., description="ID core_catalogs"),
    offering_id: int = Query(..., description="ID core_offerings"),
    resource_id: Optional[int] = Query(None, description="ID core_resources"),
    worker_id: Optional[int] = Query(None, description="ID core_workers"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Consulta slots disponíveis via scheduling engine genérico.

    Delega conflitos ao motor legado; retorna vocabulário CoreFlow v1.

    Args:
        date: Data da consulta.
        catalog_id: Catálogo genérico.
        offering_id: Offering genérico.
        resource_id: Recurso opcional.
        worker_id: Profissional opcional.

    Returns:
        Lista de slots com flag ``available``.
    """
    try:
        return SchedulingAvailabilityService(db).get_availability(
            company_id=tenant.company_id,
            target_date=date,
            catalog_id=catalog_id,
            offering_id=offering_id,
            resource_id=resource_id,
            worker_id=worker_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@scheduling_router.post("/conflicts", response_model=ConflictCheckResponse)
def verificar_conflito(
    body: ConflictCheckRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detecta conflito de alocação em resource (Scheduling Engine).

    Args:
        body: Resource + janela temporal.

    Returns:
        ConflictCheckResponse.
    """
    from app.modules.scheduling.engine.scheduling_engine import SchedulingEngine

    try:
        result = SchedulingEngine(db).detect_conflict(
            company_id=tenant.company_id,
            resource_id=body.resource_id,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
        )
        return ConflictCheckResponse(
            has_conflict=result.has_conflict,
            resource_id=result.resource_id,
            capacity=result.capacity,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
