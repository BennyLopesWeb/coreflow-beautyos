"""Testes CF-6 — core_payments + OpenTelemetry config."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.payments.application.legacy_sync_service import PaymentLegacySyncService
from app.modules.payments.domain.models import CorePayment
from app.core.config import settings


def _project_booking(db, company_id, cliente_exemplo, synced_catalog, days_ahead: int) -> int:
    """
    Cria um ``CoreBooking`` core-only via ``CreateBookingHandler`` (R4-F8).

    .. deprecated:: 2.11.0-r4-f8
        Substitui a criação direta de ``Agendamento`` legado (a tabela
        ``agendamentos`` foi removida via DROP físico — ADR-024 sunset /
        RFC-003 M11+). O booking criado é sempre core-only
        (``legacy_agendamento_id=None``); usado para exercitar
        ``PaymentLegacySyncService`` no path ``Payment.booking_id``
        (bridge R4-F6).

    Args:
        db: Sessão SQLAlchemy de teste.
        company_id: Tenant.
        cliente_exemplo: Fixture de cliente.
        synced_catalog: Tupla (CoreCatalog, CoreOffering) sincronizada.
        days_ahead: Dias à frente para o slot.

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
        datetime.now() + timedelta(days=days_ahead),
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


def test_payment_sync_from_legacy(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Sync cria core_payment a partir de Payment com booking_id (R4-F6/R4-F8)."""
    booking_id = _project_booking(
        db, default_company.id, cliente_exemplo, synced_catalog, days_ahead=4
    )

    pag = Payment(
        booking_id=booking_id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("45.00"),
        status=PaymentStatus.PENDING,
    )
    db.add(pag)
    db.commit()
    db.refresh(pag)

    PaymentLegacySyncService(db).sync_all()
    row = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .first()
    )
    assert row is not None
    assert row.booking_id == booking_id
    assert row.amount == Decimal("45.00")


def test_v1_payments_by_booking_id(
    client, admin_headers, default_company, cliente_exemplo, synced_catalog, db
):
    """GET /v1/payments?booking_id= retorna pagamentos sync (R4-F8 — sem agendamento_id)."""
    booking_id = _project_booking(
        db, default_company.id, cliente_exemplo, synced_catalog, days_ahead=5
    )

    pag = Payment(
        booking_id=booking_id,
        tipo=PaymentType.DEPOSIT,
        valor=Decimal("45.00"),
        status=PaymentStatus.PENDING,
    )
    db.add(pag)
    db.commit()
    PaymentLegacySyncService(db).sync_all()

    response = client.get(
        "/v1/payments",
        params={"booking_id": booking_id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["booking_id"] == booking_id


def test_otel_disabled_by_default():
    """OpenTelemetry desligado por padrão em dev/test."""
    assert settings.OTEL_ENABLED is False
