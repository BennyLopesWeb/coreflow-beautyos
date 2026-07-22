"""
Router API v1 — Bookings (metamodelo CoreFlow + CQRS).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.db.session import get_db
from sqlalchemy.orm import Session

from app.core.architecture_metrics import ArchitectureMetricsStore
from app.core.exceptions import (
    BusinessRuleError,
    CancelPolicyViolationError,
    ConflictError,
    DepositRequiredError,
    IdempotencyKeyRequiredError,
    IdempotencyKeyReusedError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.modules.identity.api.deps import get_tenant_context, get_current_admin_user
from app.models.user import User
from app.shared.kernel.tenant import TenantContext
from app.modules.booking.application.commands.create_booking import (
    CreateBookingCommand,
    CreateBookingHandler,
)
from app.modules.booking.application.commands.approve_booking import (
    ApproveBookingCommand,
    ApproveBookingHandler,
)
from app.modules.booking.application.commands.reject_booking import (
    RejectBookingCommand,
    RejectBookingHandler,
)
from app.modules.booking.application.commands.cancel_booking import (
    CancelBookingCommand,
    CancelBookingHandler,
)
from app.modules.booking.application.commands.reschedule_booking import (
    RescheduleBookingCommand,
    RescheduleBookingHandler,
)
from app.modules.booking.application.booking_query_service import BookingQueryService
from app.modules.booking.application.booking_response import booking_to_response_dict
from app.schemas.coreflow_v1 import (
    BookingCancelRequest,
    BookingCreateRequest,
    BookingRejectRequest,
    BookingRescheduleRequest,
    BookingRescheduleResponse,
    BookingResponse,
)
from app.shared.idempotency.request_hash import compute_request_hash

router = APIRouter(prefix="/v1/bookings", tags=["CoreFlow — Bookings"])


def _parse_if_match(if_match: Optional[str]) -> Optional[int]:
    """
    Extrai version de header If-Match (ADR-031).

    Args:
        if_match: Valor bruto do header (ex.: W/\"3\").

    Returns:
        Inteiro version ou None se ausente.
    """
    if not if_match:
        return None
    cleaned = if_match.strip()
    if cleaned.upper().startswith("W/"):
        cleaned = cleaned[2:].strip()
    cleaned = cleaned.strip('"')
    try:
        return int(cleaned)
    except ValueError:
        return None


def _to_booking_response(booking) -> BookingResponse:
    """
    Serializa CoreBooking para DTO.

    Args:
        booking: Instância CoreBooking com relações carregadas.

    Returns:
        BookingResponse.
    """
    data = booking_to_response_dict(booking)
    return BookingResponse(**data)


@router.post("", response_model=BookingResponse)
def criar_booking(
    body: BookingCreateRequest,
    response: Response,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Cria booking via CQRS com Idempotency-Key obrigatório (ADR-031 / R2-F1b).

    Args:
        body: customer_id, catalog_id, offering_id, scheduled_at.
        idempotency_key: UUID v4 — retry seguro.
        correlation_id: Rastreio opcional; gerado se ausente.

    Returns:
        BookingResponse com legacy_agendamento_id para integração.
    """
    if not idempotency_key or not idempotency_key.strip():
        ArchitectureMetricsStore.get().record_idempotency_missing_key()
        raise IdempotencyKeyRequiredError()

    corr = correlation_id or str(uuid.uuid4())
    payload = body.model_dump(mode="json")
    request_hash = compute_request_hash(payload)

    handler = CreateBookingHandler(db)
    try:
        cmd = CreateBookingCommand(
            customer_id=body.customer_id,
            catalog_id=body.catalog_id,
            offering_id=body.offering_id,
            scheduled_at=body.scheduled_at,
            company_id=tenant.company_id,
            notes=body.notes,
            idempotency_key=idempotency_key.strip(),
            request_hash=request_hash,
            correlation_id=corr,
            resource_id=body.resource_id,
        )
        result = handler.execute(cmd)
        booking = BookingQueryService(db).get_booking(
            result.booking.id, tenant.company_id
        )
        response.status_code = result.http_status
        return _to_booking_response(booking)
    except IdempotencyKeyReusedError as exc:
        raise HTTPException(status_code=409, detail=exc.detail)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=List[BookingResponse])
def listar_bookings(
    customer_id: Optional[int] = None,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Lista bookings do tenant (admin).

    Returns:
        Lista de bookings genéricos.
    """
    rows = BookingQueryService(db).list_bookings(
        tenant.company_id, customer_id=customer_id
    )
    return [_to_booking_response(b) for b in rows]


@router.get("/{booking_id}", response_model=BookingResponse)
def obter_booking(
    booking_id: int,
    response: Response,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Detalhe de um booking genérico com ETag W/\"{version}\" (R2-F2).

    Args:
        booking_id: ID core_bookings.

    Returns:
        BookingResponse.
    """
    try:
        booking = BookingQueryService(db).get_booking(booking_id, tenant.company_id)
        response.headers["ETag"] = f'W/"{booking.version or 1}"'
        return _to_booking_response(booking)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{booking_id}/approve", response_model=BookingResponse)
def aprovar_booking(
    booking_id: int,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Aprova booking genérico (admin) — domain path R2-F2 quando flag ON.

    Args:
        booking_id: ID core_bookings.
        if_match: Versão optimistic lock opcional.
        correlation_id: Rastreio outbox.

    Returns:
        BookingResponse atualizado.
    """
    handler = ApproveBookingHandler(db)
    expected = _parse_if_match(if_match)
    if if_match and expected is None:
        raise HTTPException(status_code=412, detail="precondition_failed")
    try:
        core = handler.execute(
            ApproveBookingCommand(
                booking_id=booking_id,
                company_id=tenant.company_id,
                expected_version=expected,
                correlation_id=correlation_id or str(uuid.uuid4()),
            )
        )
        booking = BookingQueryService(db).get_booking(core.id, tenant.company_id)
        return _to_booking_response(booking)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DepositRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except (ValidationError,) as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))


@router.post("/{booking_id}/reject", response_model=BookingResponse)
def rejeitar_booking(
    booking_id: int,
    body: BookingRejectRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Rejeita booking genérico (admin) — domain path R2-F2 quando flag ON.

    Args:
        booking_id: ID core_bookings.
        body: Motivo da rejeição.
        if_match: Versão optimistic lock opcional.

    Returns:
        BookingResponse atualizado.
    """
    handler = RejectBookingHandler(db)
    expected = _parse_if_match(if_match)
    if if_match and expected is None:
        raise HTTPException(status_code=412, detail="precondition_failed")
    try:
        core = handler.execute(
            RejectBookingCommand(
                booking_id=booking_id,
                company_id=tenant.company_id,
                reason=body.reason,
                expected_version=expected,
                correlation_id=correlation_id or str(uuid.uuid4()),
            )
        )
        booking = BookingQueryService(db).get_booking(core.id, tenant.company_id)
        return _to_booking_response(booking)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancelar_booking(
    booking_id: int,
    body: BookingCancelRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Cancela booking genérico (admin) — domain path R2-F2b quando flag ON.

    Args:
        booking_id: ID core_bookings.
        body: Motivo opcional.
        if_match: Versão optimistic lock opcional.
        correlation_id: Rastreio outbox.

    Returns:
        BookingResponse atualizado.
    """
    handler = CancelBookingHandler(db)
    expected = _parse_if_match(if_match)
    if if_match and expected is None:
        raise HTTPException(status_code=412, detail="precondition_failed")
    try:
        core = handler.execute(
            CancelBookingCommand(
                booking_id=booking_id,
                company_id=tenant.company_id,
                reason=body.reason,
                expected_version=expected,
                correlation_id=correlation_id or str(uuid.uuid4()),
            )
        )
        return BookingResponse(**booking_to_response_dict(core))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CancelPolicyViolationError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))


@router.post("/{booking_id}/reschedule", response_model=BookingRescheduleResponse)
def reagendar_booking(
    booking_id: int,
    body: BookingRescheduleRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id"),
):
    """
    Reagenda booking approved — fecha como ``rescheduled`` e cria substituto (R4-F11).

    Args:
        booking_id: ID do booking a substituir.
        body: Novo ``scheduled_at`` e notes opcionais.
        if_match: Versão optimistic lock opcional do booking antigo.
        correlation_id: Rastreio outbox.

    Returns:
        BookingRescheduleResponse com previous + novo booking.
    """
    handler = RescheduleBookingHandler(db)
    expected = _parse_if_match(if_match)
    if if_match and expected is None:
        raise HTTPException(status_code=412, detail="precondition_failed")
    try:
        result = handler.execute(
            RescheduleBookingCommand(
                booking_id=booking_id,
                company_id=tenant.company_id,
                scheduled_at=body.scheduled_at,
                notes=body.notes,
                expected_version=expected,
                correlation_id=correlation_id or str(uuid.uuid4()),
                resource_id=body.resource_id,
            )
        )
        prev_status = (
            result.previous.status.value
            if hasattr(result.previous.status, "value")
            else str(result.previous.status)
        )
        return BookingRescheduleResponse(
            previous_booking_id=result.previous.id,
            previous_status=prev_status,
            booking=_to_booking_response(result.booking),
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except VersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=409, detail=str(exc.detail))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc.detail))
