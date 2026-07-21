"""Testes CF-6 — core_payments + OpenTelemetry config."""
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.payments.application.legacy_sync_service import PaymentLegacySyncService
from app.modules.payments.domain.models import CorePayment
from app.core.config import settings


def _slot_disponivel(db, tranca_id: int, service_image_id: int, days_ahead: int = 4) -> datetime:
    """
    Retorna o primeiro horário disponível para reserva nos testes.

    Args:
        db: Sessão SQLAlchemy de teste.
        tranca_id: ID da trança legado.
        service_image_id: ID do modelo (service image).
        days_ahead: Dias à frente para buscar slots.

    Returns:
        datetime do slot disponível.
    """
    from app.services.disponibilidade_service import DisponibilidadeService

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        tranca_id,
        service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _project_booking(db, company_id, cliente_exemplo, tranca_exemplo, service_image_exemplo, days_ahead: int) -> int:
    """
    Cria agendamento legado diretamente via ORM (R4-F3 — sem dual-write outbound).

    Substitui o antigo ``LegacyBookingAdapter.project_create_booking``
    (removido em R4-F3 / ADR-024 sunset) por criação direta do
    ``Agendamento`` + pagamento pendente via ``PaymentReservationService``,
    já que o path core não gera mais essas linhas. Usado apenas para
    exercitar os serviços de sync legado→core (``PaymentLegacySyncService``)
    que continuam dependendo de dados legado existentes.

    Args:
        db: Sessão SQLAlchemy de teste.
        company_id: Tenant.
        cliente_exemplo: Fixture de cliente.
        tranca_exemplo: Fixture de categoria (tranca).
        service_image_exemplo: Fixture de modelo (service image).
        days_ahead: Dias à frente para o slot.

    Returns:
        ID do agendamento legado criado.
    """
    from decimal import Decimal

    from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
    from app.models.payment import PaymentType
    from app.services.payment_reservation_service import PaymentReservationService
    from app.utils.service_image_precos import resolver_precos_imagem

    slot = _slot_disponivel(db, tranca_exemplo.id, service_image_exemplo.id, days_ahead)
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


def test_payment_sync_from_legacy(
    db, default_company, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """Sync cria core_payment a partir de Payment legado."""
    ag_id = _project_booking(
        db, default_company.id, cliente_exemplo, tranca_exemplo, service_image_exemplo, days_ahead=4
    )

    pag = Payment(
        agendamento_id=ag_id,
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
    assert row.legacy_agendamento_id == ag_id
    assert row.amount == Decimal("45.00")


def test_v1_payments_by_legacy_agendamento(
    client, admin_headers, default_company, cliente_exemplo, tranca_exemplo, service_image_exemplo, db
):
    """GET /v1/payments?legacy_agendamento_id= retorna pagamentos sync."""
    ag_id = _project_booking(
        db, default_company.id, cliente_exemplo, tranca_exemplo, service_image_exemplo, days_ahead=5
    )

    response = client.get(
        "/v1/payments",
        params={"legacy_agendamento_id": ag_id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["legacy_agendamento_id"] == ag_id


def test_otel_disabled_by_default():
    """OpenTelemetry desligado por padrão em dev/test."""
    assert settings.OTEL_ENABLED is False
