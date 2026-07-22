"""Testes CF-9 — core_orders, core_invoices, workflow editor, enforcement gradual."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.modules.invoice.application.legacy_sync_service import InvoiceLegacySyncService
from app.modules.invoice.domain.models import CoreInvoice
from app.modules.order.application.legacy_sync_service import OrderLegacySyncService
from app.modules.order.domain.models import CoreOrder
from app.modules.workflow.application.workflow_definition_service import WorkflowDefinitionService
from app.modules.workflow.domain.models import CoreWorkflowRun, WorkflowRunStatus
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.shared.events.domain_event import DomainEvent
from app.core.config import settings


def _project_booking(db, company_id, cliente_exemplo, synced_catalog) -> int:
    """
    Cria um ``CoreBooking`` core-only via ``CreateBookingHandler`` (R4-F8).

    .. deprecated:: 2.11.0-r4-f8
        Substitui a criação direta de ``Agendamento`` legado (a tabela
        ``agendamentos`` foi removida via DROP físico — ADR-024 sunset /
        RFC-003 M11+). Usado para exercitar os serviços de sync
        core→genérico (``OrderLegacySyncService``/``InvoiceLegacySyncService``)
        com dados core-only.

    Args:
        db: Sessão SQLAlchemy de teste.
        company_id: Tenant.
        cliente_exemplo: Fixture de cliente.
        synced_catalog: Tupla (CoreCatalog, CoreOffering) sincronizada.

    Returns:
        ID do ``core_bookings`` criado.
    """
    from app.modules.booking.application.commands.create_booking import (
        CreateBookingCommand,
        CreateBookingHandler,
    )
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=3),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    result = CreateBookingHandler(db).execute(
        CreateBookingCommand(
            customer_id=cliente_exemplo.id,
            catalog_id=catalog.id,
            offering_id=offering.id,
            scheduled_at=slot.horario,
            company_id=company_id,
        )
    )
    return result.booking.id


def test_order_sync_from_booking(
    db, cliente_exemplo, synced_catalog, default_company
):
    """Sync cria core_order a partir de um CoreBooking (R4-F8 — booking_id, sem agendamento legado)."""
    booking_id = _project_booking(db, default_company.id, cliente_exemplo, synced_catalog)
    OrderLegacySyncService(db).sync_one(booking_id)

    row = (
        db.query(CoreOrder)
        .filter(CoreOrder.booking_id == booking_id)
        .first()
    )
    assert row is not None
    assert row.total_amount == Decimal("150.00")
    assert row.customer_id == cliente_exemplo.id


def test_invoice_sync_from_financeiro(
    db, cliente_exemplo, synced_catalog, default_company
):
    """Sync cria core_invoice a partir de entrada financeira (R4-F8 — sem link a agendamento legado)."""
    booking_id = _project_booking(db, default_company.id, cliente_exemplo, synced_catalog)
    OrderLegacySyncService(db).sync_one(booking_id)

    from app.services.financeiro_service import FinanceiroService

    mov = FinanceiroService(db).registrar_entrada_automatica(
        descricao=f"Sinal - Booking #{booking_id}",
        valor=Decimal("45.00"),
        agendamento_id=None,
    )
    InvoiceLegacySyncService(db).sync_all()

    inv = (
        db.query(CoreInvoice)
        .filter(CoreInvoice.legacy_financeiro_id == mov.id)
        .first()
    )
    assert inv is not None
    assert inv.amount == mov.valor
    assert inv.invoice_number.startswith("INV-")


def test_v1_orders_and_invoices_list(
    client, admin_headers, synced_catalog, cliente_exemplo, db,
    default_company,
):
    """GET /v1/orders e /v1/invoices retornam dados sincronizados a partir de CoreBooking (R4-F9).

    A tabela ``agendamentos`` foi removida (DROP físico) — o booking usado
    como fonte do sync (``OrderLegacySyncService``) é criado via
    ``CreateBookingHandler`` (core-only). A entrada financeira é criada
    automaticamente por ``confirmar_deposito_por_booking`` (R4-F9).
    """
    from app.services.payment_reservation_service import PaymentReservationService

    booking_id = _project_booking(
        db, default_company.id, cliente_exemplo, synced_catalog
    )
    OrderLegacySyncService(db).sync_one(booking_id)
    PaymentReservationService(db).confirmar_deposito_por_booking(booking_id)

    orders_resp = client.get("/v1/orders", headers=admin_headers)
    assert orders_resp.status_code == 200
    assert len(orders_resp.json()) >= 1

    invoices_resp = client.get("/v1/invoices", headers=admin_headers)
    assert invoices_resp.status_code == 200
    assert len(invoices_resp.json()) >= 1


def test_workflow_definitions_and_disable(
    client, admin_headers, db, default_company
):
    """GET/PATCH /v1/workflows/definitions controla habilitação."""
    defs_resp = client.get("/v1/workflows/definitions", headers=admin_headers)
    assert defs_resp.status_code == 200
    defs = defs_resp.json()
    assert len(defs) >= 1
    wf_id = defs[0]["workflow_id"]

    patch_resp = client.patch(
        f"/v1/workflows/definitions/{wf_id}",
        json={"enabled": False},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["enabled"] is False

    engine = WorkflowEngine()
    engine.load_all()
    event = DomainEvent(
        event_type=defs[0]["trigger"],
        company_id=default_company.id,
        payload={"agendamento_id": 1},
    )
    runs = engine.process_event(db, event)
    assert runs == []


def test_enforcement_mode_default_off():
    """Enforcement gradual desligado por padrão."""
    assert settings.CORE_ENFORCEMENT_MODE == "off"
