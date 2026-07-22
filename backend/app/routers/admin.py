"""
Router administrativo — dashboard, pagamentos, agenda, CRM e agente IA.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.db.session import get_db
from app.core.dependencies import get_current_admin_user as get_current_admin
from app.models.user import User
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


@router.get("/dashboard", response_model=AdminDashboardResponse)
def obter_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Retorna métricas agregadas para o dashboard administrativo.
    """
    return AdminService(db).obter_dashboard()


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
    _: User = Depends(get_current_admin),
):
    """
    Lista todos os agendamentos com status de pagamento do sinal.
    """
    return AdminService(db).listar_pagamentos()


@router.get("/agenda", response_model=List[AgendamentoAdminItem])
def listar_agenda_admin(
    data: Optional[date] = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Lista agendamentos para gestão admin, com opção de filtro por data.
    """
    return AdminService(db).listar_agendamentos(data_ref=data)


@router.patch("/agenda/{agendamento_id}/status", response_model=AgendamentoAdminItem)
def atualizar_status_agenda(
    agendamento_id: int,
    body: AtualizarStatusAgendamentoRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Atualiza o status de um agendamento (confirmar, cancelar, concluir).
    """
    service = AdminService(db)
    booking = service.atualizar_status_agendamento(agendamento_id, body.status)
    items = service.listar_agendamentos(data_ref=booking.scheduled_at.date())
    for item in items:
        if item.id == agendamento_id:
            return item
    if items:
        return items[0]

    from app.modules.catalog.domain.models import CoreCatalog
    catalog = db.query(CoreCatalog).filter(CoreCatalog.id == booking.catalog_id).first()
    return AgendamentoAdminItem(
        id=booking.id,
        cliente_id=booking.customer_id,
        cliente_nome="",
        cliente_telefone="",
        tranca_id=(catalog.legacy_tranca_id if catalog else None) or booking.catalog_id,
        tranca_nome="",
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
    _: User = Depends(get_current_admin),
):
    """
    Admin confirma recebimento do sinal diretamente em ``core_bookings`` (R4-F4).

    Path primário desde R4-F4: bookings core-only (criados via
    ``POST /v1/bookings``) não têm ``Agendamento`` associado, então a
    confirmação do sinal deve atualizar ``CoreBooking.deposit_paid``
    diretamente via ``PaymentReservationService.confirmar_deposito_por_booking``
    (mesmo path usado por ``/v1/bookings/{id}/approve``, ADR-028).

    Args:
        booking_id: ID ``core_bookings.id``.
        db: Sessão SQLAlchemy.

    Returns:
        Dict com ``id``, ``status`` e ``deposit_paid`` do booking atualizado.
    """
    from app.services.payment_reservation_service import PaymentReservationService

    try:
        booking = PaymentReservationService(db).confirmar_deposito_por_booking(booking_id)
        return {
            "id": booking.id,
            "status": booking.status.value,
            "deposit_paid": booking.deposit_paid,
        }
    except Exception as e:
        from fastapi import HTTPException, status
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
