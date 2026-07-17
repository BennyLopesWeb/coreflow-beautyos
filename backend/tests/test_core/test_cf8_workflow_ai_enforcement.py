"""Testes CF-8 — workflow engine + LLM providers + core enforcement."""
from datetime import datetime, timedelta

from app.core.core_enforcement import CoreEnforcementMiddleware, match_legacy_write
from app.modules.ai.llm_service import LLMService
from app.modules.workflow.domain.models import CoreWorkflowRun, WorkflowRunStatus
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.shared.events.domain_event import DomainEvent
from app.shared.events.outbox import CoreEventOutbox, OutboxStatus
from app.core.config import settings


def _slot_disponivel(db, tranca_id: int, service_image_id: int) -> datetime:
    """
    Retorna primeiro horário disponível para testes.

    Args:
        db: Sessão de teste.
        tranca_id: ID tranca legado.
        service_image_id: ID service image.

    Returns:
        datetime do slot.
    """
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=3),
        tranca_id,
        service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def test_v1_approve_booking(
    client,
    admin_headers,
    synced_catalog,
    cliente_exemplo,
    tranca_exemplo,
    service_image_exemplo,
    db,
    booking_headers,
):
    """POST /v1/bookings/{id}/approve aprova reserva com sinal pago."""
    from app.services.payment_reservation_service import PaymentReservationService

    catalog, offering = synced_catalog
    slot = _slot_disponivel(db, tranca_exemplo.id, service_image_exemplo.id)

    create_resp = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert create_resp.status_code == 201, create_resp.text
    booking = create_resp.json()
    legacy_id = booking["legacy_agendamento_id"]
    assert legacy_id is not None

    PaymentReservationService(db).confirmar_deposito(legacy_id, transaction_id="test-tx")

    approve_resp = client.post(
        f"/v1/bookings/{booking['id']}/approve",
        headers=admin_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()
    assert approved["status"] in ("approved", "APPROVED")

    outbox = (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.approved",
            CoreEventOutbox.aggregate_id == str(booking["id"]),
        )
        .first()
    )
    assert outbox is not None
    assert outbox.status == OutboxStatus.PROCESSED


def test_workflow_engine_on_deposit_confirmed(db, default_company):
    """WorkflowEngine cria core_workflow_run ao receber payment.deposit.confirmed."""
    engine = WorkflowEngine()
    loaded = engine.load_all()
    assert loaded >= 1

    event = DomainEvent(
        event_type="payment.deposit.confirmed",
        company_id=default_company.id,
        aggregate_id="99",
        aggregate_type="Payment",
        payload={"agendamento_id": 1, "payment_id": 99},
    )
    runs = engine.process_event(db, event)
    assert len(runs) >= 1
    assert runs[0].status == WorkflowRunStatus.COMPLETED
    assert "notify_admin" in (runs[0].steps_executed or "")


def test_llm_mock_provider():
    """LLMService retorna mock provider por padrão."""
    LLMService.reset()
    provider = LLMService.get_provider()
    assert provider.provider_id == "mock"
    insights = provider.generate_insights({"company_id": 1, "pending_tasks": [], "capabilities": []})
    assert len(insights) >= 1


def test_core_enforcement_match_legacy_write():
    """match_legacy_write identifica POST legado com sucessor v1."""
    rule = match_legacy_write("POST", "/agenda/agendamentos")
    assert rule is not None
    assert rule.successor == "/v1/bookings"


def test_core_enforcement_middleware_blocks_when_enabled():
    """Middleware retorna 409 para escrita booking legado em modo block (ADR-033)."""
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/agenda/agendamentos", ok, methods=["POST"])])
    app.add_middleware(CoreEnforcementMiddleware, mode="block")

    with TestClient(app) as client:
        response = client.post("/agenda/agendamentos", json={})
        assert response.status_code == 409
        assert response.json()["successor"] == "/v1/bookings"
        assert response.headers.get("Deprecation") == "true"


def test_core_enforcement_warn_mode_allows_request():
    """Modo warn adiciona headers mas permite a requisição."""
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/agenda/agendamentos", ok, methods=["POST"])])
    app.add_middleware(CoreEnforcementMiddleware, mode="warn")

    with TestClient(app) as client:
        response = client.post("/agenda/agendamentos", json={})
        assert response.status_code == 200
        assert response.headers.get("X-CoreFlow-Enforcement") == "warn"


def test_ai_llm_disabled_by_default():
    """AI LLM desligado por padrão."""
    assert settings.AI_LLM_ENABLED is False
    assert settings.CORE_ENFORCEMENT_ENABLED is False
