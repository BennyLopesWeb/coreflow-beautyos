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
    Cria agendamento legado via dual-write ACL (R3-F2 — sem ReservationService).

    Substitui o antigo ``ReservationService.criar_de_schema`` (removido em
    R3-F2) usando ``LegacyBookingAdapter.project_create_booking`` — o mesmo
    caminho de projeção outbound usado pelo path core.

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
    from app.shared.acl.booking_port import LegacyBookingAdapter
    from app.utils.service_image_precos import resolver_precos_imagem

    slot = _slot_disponivel(db, tranca_exemplo.id, service_image_exemplo.id, days_ahead)
    precos = resolver_precos_imagem(service_image_exemplo)
    ag_id = LegacyBookingAdapter(db).project_create_booking(
        company_id=company_id,
        customer_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        scheduled_at=slot,
        pricing_total=precos["valor_total"],
        deposit_pct=precos["percentual_sinal"],
        deposit_amount=precos["valor_sinal"],
        remaining_amount=precos["valor_restante"],
    )
    db.commit()
    return ag_id


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
