"""
R4-F6 - Bridge Payment -> booking_id + cutover disponibilidade core-only - ADR-024 / RFC-003 M10.

Sucede test_r4_f5_core_ops.py (FK booking_id em QueueEntry/Fila + fechamento
do gap operacional). O gate R4-F5 documentou dois debitos residuais que
esta sprint fecha:

1. ``payments.agendamento_id`` era obrigatorio - pagamentos de bookings
   core-only (sem ``Agendamento`` associado) nao tinham como ser
   persistidos em ``payments`` via vinculo direto.
2. Admin de pagamentos legado (``/admin/pagamentos/{agendamento_id}/
   confirmar-sinal``) permanecia dual-path apenas marcado ``deprecated``.

Prova que:

- APP_VERSION == 2.9.0-r4-f6.
- ``Payment`` aceita ``booking_id`` sem ``agendamento_id`` (bridge).
- ``PaymentReservationService.criar_pendente`` recusa quando nem
  ``agendamento_id`` nem ``booking_id`` sao informados.
- ``confirmar_deposito_por_booking`` cria/atualiza um ``Payment`` ponte
  vinculado por ``booking_id``.
- ``DisponibilidadeService`` marca slot ocupado por ``CoreBooking`` sem
  nenhuma linha em ``agendamentos`` (banco completamente vazio de
  legado).
- ``DisponibilidadeService.expirar_reservas_pendentes`` cancela
  ``CoreBooking`` pendente sem sinal pago (equivalente ao expirar de
  ``Agendamento`` legado, mas via ``CancelBookingHandler``).
- ``ReservationService.aceitar_reagendamento`` nao cria mais ``Schedule``.
- ``POST /admin/pagamentos/{agendamento_id}/confirmar-sinal`` retorna
  410 Gone.
- ``POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal``
  continua funcional (path unico desde esta release).

O DROP fisico de ``agendamentos``/``payments``/``schedules`` continua
fora de escopo - explicitamente adiado para **R4-F7** (``Schedule``/
``SatisfactionSurvey`` ainda referenciam ``agendamentos``; ver
docs/sprints/R4-F6.md).
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessRuleError
from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.models.schedule import Schedule
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.payment_reservation_service import PaymentReservationService
from app.services.reservation_service import ReservationService


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro horário disponível N dias à frente.

    Args:
        db: Sessão SQLAlchemy de teste.
        catalog: Fixture CoreCatalog sincronizado.
        offering: Fixture CoreOffering sincronizado.
        days_ahead: Deslocamento em dias para o slot candidato.

    Returns:
        datetime do primeiro horário disponível encontrado.
    """
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _create_booking(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead: int) -> dict:
    """
    Cria booking via ``POST /v1/bookings`` - sempre core-only (R4-F3+).

    Args:
        client: TestClient FastAPI.
        db: Sessão SQLAlchemy de teste.
        synced_catalog: Tupla (CoreCatalog, CoreOffering) sincronizados.
        cliente_exemplo: Fixture de cliente legado.
        booking_headers: Factory de headers Idempotency-Key.
        days_ahead: Deslocamento em dias para o slot.

    Returns:
        Dict JSON do booking criado (resposta 201).
    """
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead)
    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_app_version_r4_f6():
    """APP_VERSION marca a release R4-F6 (bridge Payment→booking_id)."""
    assert settings.APP_VERSION == "2.9.0-r4-f6"


def test_payment_aceita_booking_id_sem_agendamento_id(db, default_company, cliente_exemplo, synced_catalog):
    """Payment model persiste com booking_id preenchido e agendamento_id=None (bridge R4-F6)."""
    catalog, offering = synced_catalog
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=80),
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

    pag = PaymentReservationService(db).criar_pendente(
        None, PaymentType.DEPOSIT, Decimal("30.00"), booking_id=booking.id
    )

    assert pag.id is not None
    assert pag.agendamento_id is None
    assert pag.booking_id == booking.id

    reloaded = db.query(Payment).filter(Payment.id == pag.id).first()
    assert reloaded.agendamento_id is None
    assert reloaded.booking_id == booking.id


def test_criar_pendente_falha_sem_agendamento_e_sem_booking(db):
    """PaymentReservationService.criar_pendente recusa sem agendamento_id nem booking_id."""
    with pytest.raises(BusinessRuleError, match="agendamento_id"):
        PaymentReservationService(db).criar_pendente(None, PaymentType.DEPOSIT, Decimal("10.00"))


def test_confirmar_deposito_por_booking_cria_payment_ponte(
    db, default_company, cliente_exemplo, synced_catalog
):
    """confirmar_deposito_por_booking cria Payment vinculado por booking_id (sem Agendamento)."""
    catalog, offering = synced_catalog
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=81),
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

    assert db.query(Agendamento).count() == 0

    atualizado = PaymentReservationService(db).confirmar_deposito_por_booking(booking.id)

    assert atualizado.deposit_paid is True

    pag = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    assert pag is not None
    assert pag.agendamento_id is None
    assert pag.status == PaymentStatus.PAID
    assert db.query(Agendamento).count() == 0


def test_disponibilidade_marca_slot_ocupado_por_core_booking_sem_agendamento(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """DisponibilidadeService core-only marca slot ocupado com banco 100% sem Agendamento."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=82)

    assert db.query(Agendamento).count() == 0

    response = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert response.status_code == 201, response.text

    # Nenhuma linha em agendamentos foi criada — cutover core-only completo.
    assert db.query(Agendamento).count() == 0

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        slot, catalog.legacy_tranca_id, offering.legacy_service_image_id
    )
    ocupado = next(h for h in horarios if h.horario == slot)
    assert ocupado.disponivel is False


def test_expirar_core_bookings_pendentes_sem_sinal(
    db, default_company, cliente_exemplo, synced_catalog
):
    """expirar_reservas_pendentes cancela CoreBooking pendente/sem sinal pago via CancelBookingHandler."""
    catalog, offering = synced_catalog
    limite = datetime.now() - timedelta(hours=3)
    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=83),
        status=ReservationStatus.PENDING_PAYMENT,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=False,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=limite,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    booking_id = booking.id

    count = DisponibilidadeService(db).expirar_reservas_pendentes()

    assert count >= 1
    db.expire_all()
    expirado = db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
    assert expirado.status == ReservationStatus.CANCELLED


def test_expirar_nao_cancela_core_booking_recente_ou_com_sinal(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """expirar_reservas_pendentes não cancela CoreBooking recente (dentro do prazo)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=84
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    ainda_ativo = db.query(CoreBooking).filter(CoreBooking.id == booking["id"]).first()
    assert ainda_ativo.status != ReservationStatus.CANCELLED


def test_aceitar_reagendamento_nao_cria_schedule(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """aceitar_reagendamento transita status sem criar Schedule (R4-F6 — parada de escrita legado)."""
    from app.utils.service_image_precos import resolver_precos_imagem

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    horario_sugerido = datetime.now() + timedelta(days=85)
    agendamento = Agendamento(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=datetime.now() + timedelta(days=86),
        status=ReservationStatus.WAITING_TIME_CONFIRMATION,
        horario_sugerido=horario_sugerido,
        sinal_pago=True,
        valor_total=precos["valor_total"],
        percentual_sinal=service_image_exemplo.percentual_sinal or Decimal("0.30"),
        valor_sinal=precos["valor_sinal"],
        valor_restante=precos["valor_restante"],
        status_pagamento=StatusPagamento.PARTIALLY_PAID,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)

    atualizado = ReservationService(db).aceitar_reagendamento(agendamento.id)

    assert atualizado.status == ReservationStatus.APPROVED
    assert atualizado.horario_aprovado == horario_sugerido

    schedule = (
        db.query(Schedule).filter(Schedule.agendamento_id == agendamento.id).first()
    )
    assert schedule is None


def test_admin_confirmar_sinal_legado_retorna_410(
    client, admin_headers, cliente_exemplo, tranca_exemplo, service_image_exemplo, default_company, db
):
    """POST /admin/pagamentos/{agendamento_id}/confirmar-sinal responde 410 Gone (R4-F6)."""
    from app.utils.service_image_precos import resolver_precos_imagem

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    agendamento = Agendamento(
        company_id=default_company.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=datetime.now() + timedelta(days=87),
        status=ReservationStatus.PENDING_PAYMENT,
        sinal_pago=False,
        valor_total=precos["valor_total"],
        percentual_sinal=service_image_exemplo.percentual_sinal or Decimal("0.30"),
        valor_sinal=precos["valor_sinal"],
        valor_restante=precos["valor_restante"],
        status_pagamento=StatusPagamento.PENDING_PAYMENT,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)

    response = client.post(
        f"/admin/pagamentos/{agendamento.id}/confirmar-sinal",
        headers=admin_headers,
    )

    assert response.status_code == 410, response.text
    body = response.json()
    assert body["status"] == 410
    assert "booking" in body["successor"]

    # Confirma que a rota removida não altera o agendamento legado.
    db.refresh(agendamento)
    assert agendamento.sinal_pago is False


def test_admin_confirmar_sinal_booking_continua_funcional(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal continua funcional (path único)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=88
    )

    response = client.post(
        f"/admin/pagamentos/booking/{booking['id']}/confirmar-sinal",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deposit_paid"] is True

    pag = db.query(Payment).filter(Payment.booking_id == booking["id"]).first()
    assert pag is not None
    assert pag.status == PaymentStatus.PAID
