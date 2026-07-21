"""Testes CF-9 — core_orders, core_invoices, workflow editor, enforcement gradual."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.financeiro import Financeiro, TipoMovimento
from app.modules.catalog.application.legacy_sync_service import LegacySyncService
from app.modules.invoice.application.legacy_sync_service import InvoiceLegacySyncService
from app.modules.invoice.domain.models import CoreInvoice
from app.modules.order.application.legacy_sync_service import OrderLegacySyncService
from app.modules.order.domain.models import CoreOrder
from app.modules.workflow.application.workflow_definition_service import WorkflowDefinitionService
from app.modules.workflow.domain.models import CoreWorkflowRun, WorkflowRunStatus
from app.modules.workflow.engine.workflow_engine import WorkflowEngine
from app.shared.events.domain_event import DomainEvent
from app.core.config import settings


def _slot_disponivel(db, tranca_id: int, service_image_id: int) -> datetime:
    """
    Retorna primeiro horário disponível para testes.

    Args:
        db: Sessão de teste.
        tranca_id: ID tranca.
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


def _project_booking(db, company_id, cliente_exemplo, tranca_exemplo, service_image_exemplo) -> int:
    """
    Cria agendamento legado diretamente via ORM (R4-F3 — sem dual-write outbound).

    Substitui o antigo ``LegacyBookingAdapter.project_create_booking``
    (removido em R4-F3 / ADR-024 sunset) por criação direta do
    ``Agendamento`` + pagamento pendente via ``PaymentReservationService``,
    já que o path core não gera mais essas linhas. Usado apenas para
    exercitar os serviços de sync legado→core (``OrderLegacySyncService``/
    ``InvoiceLegacySyncService``) que continuam dependendo de dados legado
    existentes.

    Args:
        db: Sessão SQLAlchemy de teste.
        company_id: Tenant.
        cliente_exemplo: Fixture de cliente.
        tranca_exemplo: Fixture de categoria (tranca).
        service_image_exemplo: Fixture de modelo (service image).

    Returns:
        ID do agendamento legado criado.
    """
    from decimal import Decimal

    from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
    from app.models.payment import PaymentType
    from app.services.payment_reservation_service import PaymentReservationService
    from app.utils.service_image_precos import resolver_precos_imagem

    slot = _slot_disponivel(db, tranca_exemplo.id, service_image_exemplo.id)
    precos = resolver_precos_imagem(service_image_exemplo)
    ag = Agendamento(
        company_id=company_id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=slot,
        valor_total=Decimal(str(precos["valor_total"])),
        percentual_sinal=Decimal(str(precos["percentual_sinal"])),
        valor_sinal=Decimal(str(precos["valor_sinal"])),
        valor_restante=Decimal(str(precos["valor_restante"])),
        status=ReservationStatus.PENDING_PAYMENT,
        status_pagamento=StatusPagamento.PENDING_PAYMENT,
        sinal_pago=False,
    )
    db.add(ag)
    db.commit()
    db.refresh(ag)
    PaymentReservationService(db).criar_pendente(
        ag.id, PaymentType.DEPOSIT, Decimal(str(precos["valor_sinal"]))
    )
    return ag.id


def test_order_sync_from_booking(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo, default_company
):
    """Sync cria core_order a partir de agendamento legado."""
    ag_id = _project_booking(db, default_company.id, cliente_exemplo, tranca_exemplo, service_image_exemplo)
    LegacySyncService(db).sync_all()
    OrderLegacySyncService(db).sync_one(ag_id)

    row = (
        db.query(CoreOrder)
        .filter(CoreOrder.legacy_agendamento_id == ag_id)
        .first()
    )
    assert row is not None
    assert row.total_amount == Decimal("150.00")
    assert row.customer_id == cliente_exemplo.id


def test_invoice_sync_from_financeiro(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo, default_company
):
    """Sync cria core_invoice a partir de entrada financeira."""
    from app.services.payment_reservation_service import PaymentReservationService

    ag_id = _project_booking(db, default_company.id, cliente_exemplo, tranca_exemplo, service_image_exemplo)
    PaymentReservationService(db).confirmar_deposito(ag_id, transaction_id="tx-inv")
    LegacySyncService(db).sync_all()
    OrderLegacySyncService(db).sync_all()
    InvoiceLegacySyncService(db).sync_all()

    mov = (
        db.query(Financeiro)
        .filter(
            Financeiro.agendamento_id == ag_id,
            Financeiro.tipo == TipoMovimento.ENTRADA,
        )
        .first()
    )
    assert mov is not None

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
    tranca_exemplo, service_image_exemplo, default_company,
):
    """GET /v1/orders e /v1/invoices retornam dados sincronizados a partir de agendamento legado.

    R4-F3: o dual-write outbound foi removido — o agendamento legado usado
    como fonte do sync (``OrderLegacySyncService``/``InvoiceLegacySyncService``)
    é criado diretamente via ORM (``_project_booking``), não mais via
    ``POST /v1/bookings`` + projeção.
    """
    from app.services.payment_reservation_service import PaymentReservationService

    ag_id = _project_booking(
        db, default_company.id, cliente_exemplo, tranca_exemplo, service_image_exemplo
    )
    PaymentReservationService(db).confirmar_deposito(ag_id)

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
