"""Testes CF-5 — core_customers, outbox, booking.created."""
from datetime import datetime, timedelta

from app.modules.customer.legacy_sync import CustomerLegacySyncService
from app.modules.customer.models import CoreCustomer
from app.shared.events.outbox import CoreEventOutbox, OutboxService, OutboxStatus
from app.shared.events.domain_event import DomainEvent


def test_customer_sync_from_legacy(db, cliente_exemplo, default_company):
    """Sync cria core_customer a partir de Cliente legado."""
    CustomerLegacySyncService(db).sync_all()
    row = (
        db.query(CoreCustomer)
        .filter(CoreCustomer.legacy_cliente_id == cliente_exemplo.id)
        .first()
    )
    assert row is not None
    assert row.name == cliente_exemplo.nome
    assert row.phone == cliente_exemplo.telefone
    assert row.company_id == default_company.id


def test_outbox_record_and_publish(db, default_company):
    """OutboxService persiste e marca evento como processed."""
    event = DomainEvent(
        event_type="test.event",
        company_id=default_company.id,
        payload={"foo": "bar"},
    )
    OutboxService(db).record_and_publish(event)
    db.commit()

    row = db.query(CoreEventOutbox).filter(CoreEventOutbox.event_id == event.event_id).first()
    assert row is not None
    assert row.status == OutboxStatus.PROCESSED


def test_v1_create_booking_writes_outbox(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """POST /v1/bookings grava booking.created no outbox."""
    from app.services.disponibilidade_service import DisponibilidadeService

    catalog, offering = synced_catalog
    tranca_id = catalog.legacy_tranca_id
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=4),
        tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel)

    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.horario.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 201, response.text

    outbox = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.event_type == "booking.created")
        .order_by(CoreEventOutbox.id.desc())
        .first()
    )
    assert outbox is not None
    assert outbox.status == OutboxStatus.PROCESSED


def test_v1_customers_list_admin(client, admin_headers, cliente_exemplo, db):
    """GET /v1/customers (admin) retorna customers sincronizados."""
    CustomerLegacySyncService(db).sync_all()
    response = client.get("/v1/customers", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(c["legacy_cliente_id"] == cliente_exemplo.id for c in data)
