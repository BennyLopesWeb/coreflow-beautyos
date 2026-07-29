"""
Router administrativo — dashboard, pagamentos, agenda, CRM e agente IA.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.db.session import get_db
from app.core.dependencies import get_current_admin_user as get_current_admin, security
from app.modules.identity.api.deps import (
    get_tenant_context,
    get_identity_service,
)
from app.modules.identity.application.identity_service import IdentityApplicationService
from app.models.user import User
from app.shared.kernel.tenant import TenantContext
from app.schemas.admin import (
    AdminDashboardResponse,
    PagamentoAdminItem,
    AgendamentoAdminItem,
    ClienteCrmItem,
    AtualizarStatusAgendamentoRequest,
)
from app.schemas.agente import AgentTaskResponse, AgenteExecutarResponse
from app.schemas.fila import FilaResumoResponse
from app.schemas.agenda_dia import AgendaDiaCreate, AgendaDiaResponse, AgendaDiaDetalheResponse
from app.schemas.tranca import TrancaResponse
from app.services.admin_service import AdminService
from app.services.agente_service import AgenteService
from app.services.fila_service import FilaService
from app.services.tranca_service import TrancaService
from app.services.agenda_dia_service import AgendaDiaService
from app.services.agendamento_service import AgendamentoService

router = APIRouter(prefix="/admin", tags=["Admin"])

_bearer_optional = HTTPBearer(auto_error=False)


def _require_bearer_credentials(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> HTTPAuthorizationCredentials:
    """
    Exige Bearer e responde 401 quando ausente (FIX-04 / padrão FIX-08).

    Args:
        credentials: Credenciais opcionais do header Authorization.

    Returns:
        Credenciais Bearer presentes na requisição.

    Raises:
        HTTPException: 401 se o header Authorization estiver ausente.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials


def _has_effective_company(
    identity: IdentityApplicationService,
    user: User,
    credentials: HTTPAuthorizationCredentials,
) -> bool:
    """
    Indica se o admin possui tenant efetivo (JWT ``company_id`` ou membership).

    Evita que o fallback de ``get_tenant_context`` para ``salao-demo``
    exponha listagens a usuários sem vínculo de empresa.

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


def _resolve_admin_for_payment_mutation(
    identity: IdentityApplicationService,
    credentials: HTTPAuthorizationCredentials,
    tenant: TenantContext,
) -> User:
    """
    Resolve admin autenticado para mutações financeiras (FIX-04).

    Ordem: 401 (token/usuário) → 403 (não admin) → caller aplica
    ``_has_effective_company`` (403 sem tenant).

    Args:
        identity: Serviço Identity.
        credentials: Bearer já exigido.
        tenant: Contexto de tenant da requisição.

    Returns:
        User admin ativo.

    Raises:
        HTTPException: 401 ou 403 conforme regras acima.
    """
    payload = identity.tokens.decode(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    current_user = identity.get_user_by_id(int(payload.get("sub")))
    if not current_user or not current_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not tenant.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores da empresa",
        )
    return current_user


@router.get("/dashboard", response_model=AdminDashboardResponse)
def obter_dashboard(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(_require_bearer_credentials),
):
    """
    Retorna métricas agregadas para o dashboard administrativo do tenant.

    FIX-02a: exige Bearer (401), tenant efetivo (403 sem fallback
    ``salao-demo``) e agrega Cliente/CoreBooking/Fila/Financeiro com
    ``company_id == tenant.company_id`` na SQL.

    Args:
        db: Sessão SQLAlchemy.
        tenant: Contexto de tenant da requisição.
        identity: Serviço Identity (membership / JWT).
        credentials: Bearer token (obrigatório).

    Returns:
        AdminDashboardResponse com métricas apenas do tenant ativo.
    """
    current_user = _resolve_admin_for_payment_mutation(identity, credentials, tenant)
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )
    return AdminService(db).obter_dashboard(tenant.company_id)


@router.get("/trancas", response_model=List[TrancaResponse])
def listar_trancas_admin(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Lista todas as tranças para gestão do catálogo e álbuns de fotos.
    """
    return TrancaService(db).listar_todas()


@router.get("/pagamentos", response_model=List[PagamentoAdminItem])
def listar_pagamentos(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_admin),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Lista agendamentos com status de pagamento do sinal do tenant ativo.

    Isolamento: ``CoreBooking.company_id == tenant.company_id`` (query SQL).
    Sem tenant efetivo (JWT/membership) → 403 (sem fallback silencioso).
    """
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )
    return AdminService(db).listar_pagamentos(tenant.company_id)


@router.get("/agenda", response_model=List[AgendamentoAdminItem])
def listar_agenda_admin(
    data: Optional[date] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(_require_bearer_credentials),
):
    """
    Lista agendamentos para gestão admin, com opção de filtro por data.

    FIX-02b-list: exige Bearer (401), tenant efetivo (403 sem fallback
    ``salao-demo``) e filtra ``CoreBooking.company_id`` /
    ``Fila.company_id`` na SQL do service.
    """
    current_user = _resolve_admin_for_payment_mutation(identity, credentials, tenant)
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )
    return AdminService(db).listar_agendamentos(
        company_id=tenant.company_id,
        data_ref=data,
    )


@router.patch("/agenda/{agendamento_id}/status", response_model=AgendamentoAdminItem)
def atualizar_status_agenda(
    agendamento_id: int,
    body: AtualizarStatusAgendamentoRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(_require_bearer_credentials),
):
    """
    Atualiza o status de um agendamento (confirmar, cancelar, concluir).

    FIX-02b-write: exige Bearer (401), tenant efetivo (403 sem fallback
    ``salao-demo``), filtra booking por ``id + company_id``; cross-tenant /
    inexistente → 404; transição inválida → 400; reabertura de
    cancelado/expirado → 409. Consome ``BookingPolicyResolver``.

    FIX-CANCEL-POLICY-02: ``approved → cancelled`` fora da janela configurável
    → 409 (``CancelPolicyViolationError``); ``pending → cancelled`` sem janela.
    """
    from app.core.exceptions import (
        CancelPolicyViolationError,
        ConflictError,
        NotFoundError,
        ValidationError,
    )

    current_user = _resolve_admin_for_payment_mutation(identity, credentials, tenant)
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )

    service = AdminService(db)
    try:
        booking = service.atualizar_status_agendamento(
            agendamento_id,
            body.status,
            company_id=tenant.company_id,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado",
        )
    except CancelPolicyViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        )
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.detail,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Preferir projeção da listagem tenant-scoped quando não soft-deleted.
    if booking.deleted_at is None:
        items = service.listar_agendamentos(
            company_id=tenant.company_id,
            data_ref=booking.scheduled_at.date(),
        )
        for item in items:
            if item.id == agendamento_id:
                return item

    from app.modules.catalog.domain.models import CoreCatalog
    from app.models.cliente import Cliente

    catalog = db.query(CoreCatalog).filter(CoreCatalog.id == booking.catalog_id).first()
    cliente = db.query(Cliente).filter(Cliente.id == booking.customer_id).first()
    return AgendamentoAdminItem(
        id=booking.id,
        cliente_id=booking.customer_id,
        cliente_nome=cliente.nome if cliente else "",
        cliente_telefone=cliente.telefone if cliente else "",
        tranca_id=(catalog.legacy_tranca_id if catalog else None) or booking.catalog_id,
        tranca_nome=catalog.name if catalog else "",
        data_hora=booking.scheduled_at,
        status=booking.status,
        sinal_pago=booking.deposit_paid,
        na_fila=False,
    )


@router.get("/fila/{data_ref}", response_model=FilaResumoResponse)
def consultar_fila_admin(
    data_ref: date,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Consulta fila detalhada do dia para monitoramento admin.
    """
    filas = FilaService(db).consultar_fila_detalhada(data_ref)
    return FilaResumoResponse(data=data_ref, total_pessoas=len(filas), posicoes=filas)


@router.post("/agenda/{agendamento_id}/aprovar")
def aprovar_reserva_admin(
    agendamento_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Aprova reserva após pagamento do sinal (pending_approval → confirmado).
    """
    try:
        ag = AgendamentoService(db).aprovar_reserva(agendamento_id)
        return {"id": ag.id, "status": ag.status.value, "mensagem": "Reserva confirmada"}
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/pagamentos/{agendamento_id}/confirmar-sinal",
    deprecated=True,
)
def confirmar_sinal_admin(
    agendamento_id: int,
    _: User = Depends(get_current_admin),
):
    """
    **REMOVIDO (R4-F6 — retorna 410 Gone).**

    .. deprecated:: 2.9.0-r4-f6
        Path legado (``agendamentos``/``payments``) marcado ``deprecated``
        em R4-F5 e **removido nesta release** (ADR-024 sunset / RFC-003
        M10) — retorna sempre ``410 Gone`` com ``successor`` apontando
        para o path booking-first, mesmo padrão de
        ``app.core.legacy_gone.LegacyGoneMiddleware`` (R4-F1). A rota
        permanece registrada no OpenAPI (marcada ``deprecated=True``) só
        para discoverability — nenhuma reserva/pagamento é lido ou
        escrito. Use
        ``POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal``
        (path primário desde R4-F4, único desde esta release).

    Args:
        agendamento_id: ID legado (não usado — rota sempre retorna 410).
        _: Admin autenticado (mantém exigência de auth mesmo para a rota
            removida).

    Returns:
        ``JSONResponse`` 410 Gone.
    """
    from fastapi.responses import JSONResponse

    successor = "/admin/pagamentos/booking/{booking_id}/confirmar-sinal"
    detail = (
        "Rota legado removida (R4-F6) — use "
        f"POST {successor}"
    )
    return JSONResponse(
        status_code=410,
        content={
            "type": "about:blank",
            "title": "Gone",
            "status": 410,
            "detail": detail,
            "message": detail,
            "successor": successor,
            "enforcement": "gone",
        },
        headers={
            "Deprecation": "true",
            "Link": f'<{successor}>; rel="successor-version"',
            "X-CoreFlow-Enforcement": "gone",
        },
    )


@router.post("/pagamentos/booking/{booking_id}/confirmar-sinal")
def confirmar_sinal_admin_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(_require_bearer_credentials),
):
    """
    Admin confirma recebimento do sinal diretamente em ``core_bookings`` (R4-F4).

    Path primário desde R4-F4: bookings core-only (criados via
    ``POST /v1/bookings``) não têm ``Agendamento`` associado, então a
    confirmação do sinal deve atualizar ``CoreBooking.deposit_paid``
    diretamente via ``PaymentReservationService.confirmar_deposito_por_booking``
    (mesmo path usado por ``/v1/bookings/{id}/approve``, ADR-028).

    FIX-04: exige Bearer (401), tenant efetivo (403 sem fallback
    ``salao-demo``) e filtra o booking por ``company_id`` na query;
    cross-tenant / inexistente → 404; cancelado/estornado → 409;
    reconfirmação no mesmo tenant → 200 idempotente.

    Args:
        booking_id: ID ``core_bookings.id``.
        db: Sessão SQLAlchemy.
        tenant: Contexto de tenant da requisição.
        identity: Serviço Identity (membership / JWT).
        credentials: Bearer token (obrigatório).

    Returns:
        Dict com ``id``, ``status`` e ``deposit_paid`` do booking atualizado.
    """
    from app.core.exceptions import (
        BusinessRuleError,
        ConflictError,
        NotFoundError,
    )
    from app.services.payment_reservation_service import PaymentReservationService

    current_user = _resolve_admin_for_payment_mutation(identity, credentials, tenant)
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )

    try:
        booking = PaymentReservationService(db).confirmar_deposito_por_booking(
            booking_id, company_id=tenant.company_id
        )
        return {
            "id": booking.id,
            "status": booking.status.value,
            "deposit_paid": booking.deposit_paid,
        }
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking não encontrado",
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.detail,
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/pagamentos/booking/{booking_id}/confirmar-final")
def confirmar_final_admin_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
    identity: IdentityApplicationService = Depends(get_identity_service),
    credentials: HTTPAuthorizationCredentials = Depends(_require_bearer_credentials),
):
    """
    Admin confirma pagamento final (remaining) em ``core_bookings`` (R4-F10).

    Path core-only que substitui ``POST /payments/final`` (legado, 410).
    Exige sinal já confirmado (``deposit_paid``); atualiza
    ``payment_status=PAID``, cria ``Payment`` FINAL_PAYMENT e registra
    entrada ``Financeiro``.

    FIX-04: exige Bearer (401), tenant efetivo (403 sem fallback
    ``salao-demo``) e filtra o booking por ``company_id`` na query;
    cross-tenant / inexistente → 404; cancelado/estornado → 409;
    reconfirmação no mesmo tenant → 200 idempotente.

    Args:
        booking_id: ID ``core_bookings.id``.
        db: Sessão SQLAlchemy.
        tenant: Contexto de tenant da requisição.
        identity: Serviço Identity (membership / JWT).
        credentials: Bearer token (obrigatório).

    Returns:
        Dict com ``id``, ``status``, ``payment_status`` e ``deposit_paid``.
    """
    from app.core.exceptions import (
        BusinessRuleError,
        ConflictError,
        NotFoundError,
    )
    from app.services.payment_reservation_service import PaymentReservationService

    current_user = _resolve_admin_for_payment_mutation(identity, credentials, tenant)
    if not _has_effective_company(identity, current_user, credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não associado ao usuário",
        )

    try:
        booking = PaymentReservationService(db).confirmar_pagamento_final_por_booking(
            booking_id, company_id=tenant.company_id
        )
        pay_val = (
            booking.payment_status.value
            if hasattr(booking.payment_status, "value")
            else booking.payment_status
        )
        return {
            "id": booking.id,
            "status": booking.status.value,
            "payment_status": pay_val,
            "deposit_paid": booking.deposit_paid,
        }
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking não encontrado",
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.detail,
        )
    except BusinessRuleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/agenda-dia/{data_ref}", response_model=AgendaDiaDetalheResponse)
def visao_agenda_dia(
    data_ref: date,
    tranca_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Visão admin da agenda com slots disponíveis/ocupados."""
    return AgendaDiaService(db).obter_visao_dia(data_ref, tranca_id)


@router.put("/agenda-dia", response_model=AgendaDiaResponse)
def configurar_agenda_dia(
    body: AgendaDiaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Define expediente ou bloqueia um dia."""
    return AgendaDiaService(db).salvar_config(body)


@router.get("/crm/clientes", response_model=List[ClienteCrmItem])
def listar_crm_clientes(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Lista clientes com métricas de CRM (visitas, gasto, status).
    """
    return AdminService(db).listar_crm_clientes()


@router.get("/agente/tarefas", response_model=List[AgentTaskResponse])
def listar_tarefas_agente(
    apenas_pendentes: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Lista tarefas do agente inteligente de automação.
    """
    tarefas = AgenteService(db).listar_tarefas(apenas_pendentes=apenas_pendentes)
    return [AgentTaskResponse.model_validate(t) for t in tarefas]


@router.post("/agente/executar", response_model=AgenteExecutarResponse)
def executar_agente(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Executa ciclo do agente: analisa salão, cria tarefas e executa as urgentes.
    """
    return AgenteService(db).executar_automacoes()


@router.post("/agente/tarefas/{task_id}/executar", response_model=AgentTaskResponse)
def executar_tarefa_agente(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Executa manualmente uma tarefa pendente do agente.
    """
    tarefa = AgenteService(db).executar_tarefa(task_id)
    return AgentTaskResponse.model_validate(tarefa)
