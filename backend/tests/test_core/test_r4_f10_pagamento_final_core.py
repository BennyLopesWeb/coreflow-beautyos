"""R4-F10 — Pagamento final core-only + 410 em /payments/deposit|final.

Cobertura:
- APP_VERSION == 2.13.0-r4-f10.
- ``confirmar_pagamento_final_por_booking`` marca PAID + Payment FINAL + Financeiro.
- Exige ``deposit_paid``; reconfirmação não duplica Financeiro.
- Admin ``POST /admin/pagamentos/booking/{id}/confirmar-final``.
- HTTP 410 em ``/payments/deposit`` e ``/payments/final``.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.core.legacy_gone import match_legacy_gone
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.financeiro import Financeiro
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.payment_reservation_service import PaymentReservationService


def _booking(db, company, cliente, synced_catalog, *, deposit_paid: bool = True):
    """
    Cria CoreBooking de teste para R4-F10.

    Args:
        db: Sessão SQLAlchemy.
        company: Empresa seed.
        cliente: Cliente seed.
        synced_catalog: Par (catalog, offering).
        deposit_paid: Se o sinal já foi confirmado.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=95),
        status=ReservationStatus.APPROVED,
        payment_status=(
            StatusPagamento.PARTIALLY_PAID
            if deposit_paid
            else StatusPagamento.PENDING_PAYMENT
        ),
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=deposit_paid,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_app_version_r4_f10():
    """APP_VERSION avançou de R4-F10 (pin exato relaxado em R4-F11+; ver test_app_version_r4_f11)."""
    assert settings.APP_VERSION.startswith("2.")


def test_match_legacy_gone_payments_router():
    """Mapa 410 cobre /payments/deposit e /payments/final."""
    assert match_legacy_gone("/payments/deposit").successor == "/v1/payments"
    assert match_legacy_gone("/payments/deposit/admin").successor == "/v1/payments"
    assert match_legacy_gone("/payments/final").successor == "/v1/payments"
    assert match_legacy_gone("/v1/payments") is None


def test_payments_deposit_e_final_retornam_410(client):
    """POST /payments/deposit e /payments/final → 410 Gone."""
    dep = client.post("/payments/deposit", json={"agendamento_id": 1})
    assert dep.status_code == 410, dep.text
    fin = client.post("/payments/final", json={"agendamento_id": 1})
    assert fin.status_code == 410, fin.text
    assert fin.json()["successor"] == "/v1/payments"


def test_confirmar_final_exige_deposit_pago(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Sem deposit_paid, confirmar_pagamento_final_por_booking falha."""
    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog, deposit_paid=False
    )
    with pytest.raises(Exception) as exc:
        PaymentReservationService(db).confirmar_pagamento_final_por_booking(booking.id)
    assert "sinal" in str(exc.value).lower() or "deposit" in str(exc.value).lower()


def test_confirmar_final_por_booking_marca_paid_e_financeiro(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Confirma final: payment_status=PAID, Payment FINAL_PAYMENT, Financeiro."""
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)

    atualizado = PaymentReservationService(db).confirmar_pagamento_final_por_booking(
        booking.id
    )
    assert atualizado.payment_status == StatusPagamento.PAID

    pag = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.tipo == PaymentType.FINAL_PAYMENT,
        )
        .first()
    )
    assert pag is not None
    assert pag.status == PaymentStatus.PAID
    assert pag.valor == Decimal("70.00")

    movs = (
        db.query(Financeiro)
        .filter(Financeiro.descricao == f"Pagamento final - Booking #{booking.id}")
        .all()
    )
    assert len(movs) == 1
    assert movs[0].valor == Decimal("70.00")


def test_reconfirmar_final_nao_duplica_financeiro(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Segunda confirmação de final não cria outro movimento Financeiro."""
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    svc = PaymentReservationService(db)
    svc.confirmar_pagamento_final_por_booking(booking.id)
    svc.confirmar_pagamento_final_por_booking(booking.id)
    count = (
        db.query(Financeiro)
        .filter(Financeiro.descricao == f"Pagamento final - Booking #{booking.id}")
        .count()
    )
    assert count == 1


def test_admin_confirmar_final_endpoint(
    client, admin_headers, db, default_company, cliente_exemplo, synced_catalog
):
    """POST /admin/pagamentos/booking/{id}/confirmar-final confirma remaining."""
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    response = client.post(
        f"/admin/pagamentos/booking/{booking.id}/confirmar-final",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == booking.id
    assert body["payment_status"] == "paid"
    assert body["deposit_paid"] is True
