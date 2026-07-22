"""R4-F9 — Financeiro em deposit core-only + 410 em /pagamentos/sinal*.

Cobertura:
- APP_VERSION == 2.12.0-r4-f9.
- ``confirmar_deposito_por_booking`` registra entrada ``Financeiro`` na 1ª confirmação.
- Reconfirmação não duplica movimento Financeiro.
- ``match_legacy_gone`` cobre ``/pagamentos/sinal`` e ``/pagamentos/comprovante``.
- HTTP 410 Gone nas rotas legado de pagamento (via LegacyGoneMiddleware).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.core.legacy_gone import match_legacy_gone, match_booking_legacy_gone
from app.models.agendamento import ReservationStatus
from app.models.financeiro import Financeiro, TipoMovimento
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.payment_reservation_service import PaymentReservationService


def test_app_version_r4_f9():
    """APP_VERSION marca a release R4-F9 (Financeiro + sunset pagamentos)."""
    assert settings.APP_VERSION == "2.12.0-r4-f9"


def test_match_legacy_gone_pagamentos():
    """Mapa 410 cobre sinal/gerar/comprovante e preserva booking."""
    assert match_legacy_gone("/pagamentos/sinal").successor == "/v1/payments"
    assert match_legacy_gone("/pagamentos/sinal/gerar").successor == "/v1/payments"
    assert match_legacy_gone("/pagamentos/comprovante/1").successor == "/v1/payments"
    assert match_legacy_gone("/v1/payments") is None
    assert match_booking_legacy_gone("/pagamentos/sinal") is None
    assert match_booking_legacy_gone("/agenda/agendamentos").successor == "/v1/bookings"


def test_pagamentos_sinal_retorna_410(client):
    """POST /pagamentos/sinal → 410 Gone + Link successor."""
    response = client.post("/pagamentos/sinal", json={"agendamento_id": 1, "valor": 10})
    assert response.status_code == 410, response.text
    body = response.json()
    assert body["status"] == 410
    assert body["successor"] == "/v1/payments"
    assert response.headers.get("X-CoreFlow-Enforcement") == "gone"
    assert "/v1/payments" in (response.headers.get("Link") or "")


def test_pagamentos_sinal_gerar_retorna_410(client):
    """POST /pagamentos/sinal/gerar → 410 Gone."""
    response = client.post("/pagamentos/sinal/gerar", params={"agendamento_id": 1})
    assert response.status_code == 410, response.text


def test_pagamentos_comprovante_retorna_410(client):
    """POST /pagamentos/comprovante/{id} → 410 Gone."""
    response = client.post("/pagamentos/comprovante/1")
    assert response.status_code == 410, response.text


def test_confirmar_deposito_registra_financeiro(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    confirmar_deposito_por_booking cria entrada Financeiro na 1ª confirmação.

    Args (via fixtures):
        db: Sessão de teste.
        default_company: Empresa seed.
        cliente_exemplo: Cliente seed.
        synced_catalog: Par (catalog, offering) sincronizado.
    """
    catalog, offering = synced_catalog
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=90),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    PaymentReservationService(db).confirmar_deposito_por_booking(booking.id)

    movs = (
        db.query(Financeiro)
        .filter(
            Financeiro.tipo == TipoMovimento.ENTRADA,
            Financeiro.descricao == f"Sinal - Booking #{booking.id}",
        )
        .all()
    )
    assert len(movs) == 1
    assert movs[0].valor == Decimal("30.00")
    assert movs[0].agendamento_id is None


def test_reconfirmar_deposito_nao_duplica_financeiro(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Segunda chamada a confirmar_deposito_por_booking não cria outro Financeiro."""
    catalog, offering = synced_catalog
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=91),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    svc = PaymentReservationService(db)
    svc.confirmar_deposito_por_booking(booking.id)
    svc.confirmar_deposito_por_booking(booking.id)

    count = (
        db.query(Financeiro)
        .filter(Financeiro.descricao == f"Sinal - Booking #{booking.id}")
        .count()
    )
    assert count == 1
