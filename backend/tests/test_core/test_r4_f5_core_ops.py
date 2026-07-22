"""
R4-F5 — FK booking_id em QueueEntry/Fila + fechamento do gap operacional.

Sucede ``test_r4_f4_hard_sunset.py`` (Option A, sem DROP TABLE). O gate
R4-F4 documentou três débitos residuais que esta sprint fecha:

1. ``QueueEntryService.checkin``/``iniciar``/``concluir`` não avançavam
   ``core_bookings`` para entradas core-only (``agendamento_id is None``).
2. ``QueueEntry``/``Fila`` não tinham FK dedicada para ``core_bookings``
   (dedupe da fila do dia usava atributos compostos).
3. Admin de pagamentos permanecia dual-path sem sinalização de
   depreciação.

Prova que:

- APP_VERSION == 2.8.0-r4-f5.
- ``QueueEntryService.aprovar_com_horario`` seta ``entry.booking_id`` com
  o ``id`` do booking core criado.
- ``QueueEntryService.checkin``/``iniciar``/``concluir`` avançam
  ``CoreBooking.status`` (CHECKED_IN/IN_SERVICE/COMPLETED) para entradas
  core-only vinculadas por ``booking_id``.
- ``QueueEntryService.processar_reservas_do_dia`` seta ``booking_id`` ao
  criar ``QueueEntry`` a partir de ``core_bookings`` ``APPROVED`` do dia.
- ``FilaService.aprovar_fila`` seta ``fila.booking_id``.

O DROP físico de ``agendamentos``/``payments``/``schedules`` continua
fora de escopo — adiado para **R4-F6**, condicionado à migração de
``Payment``/``Schedule`` legado para o core (ver ``docs/sprints/R4-F5.md``).
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.core.config import settings
from app.models.agendamento import ReservationStatus
from app.models.fila import Fila, StatusFila
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.schemas.fila import FilaAprovarRequest
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.fila_service import FilaService
from app.services.queue_entry_service import QueueEntryService


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


def test_app_version_r4_f5():
    """APP_VERSION avançou de R4-F5 (pin exato relaxado em R4-F6+; ver test_app_version_r4_f6)."""
    assert settings.APP_VERSION.startswith("2.")


def test_aprovar_com_horario_seta_booking_id(db, synced_catalog, cliente_exemplo):
    """QueueEntryService.aprovar_com_horario vincula entry.booking_id ao booking core criado."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=70)

    entry = QueueEntry(
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        posicao=1,
        data=slot.date(),
        status=QueueEntryStatus.WAITING,
        mesmo_dia=1,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    atualizada = QueueEntryService(db).aprovar_com_horario(entry.id, slot)

    assert atualizada.booking_id is not None
    assert atualizada.agendamento_id is None

    booking = db.query(CoreBooking).filter(CoreBooking.id == atualizada.booking_id).first()
    assert booking is not None
    assert booking.customer_id == cliente_exemplo.id


def test_processar_reservas_do_dia_seta_booking_id(db, synced_catalog, cliente_exemplo, default_company):
    """QueueEntryService.processar_reservas_do_dia seta booking_id na QueueEntry criada."""
    catalog, offering = synced_catalog
    hoje = date.today()
    scheduled_at = datetime.combine(hoje, time(hour=11, minute=0))

    booking = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at,
        status=ReservationStatus.APPROVED,
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

    count = QueueEntryService(db).processar_reservas_do_dia()
    assert count >= 1

    entry = db.query(QueueEntry).filter(QueueEntry.booking_id == booking.id).first()
    assert entry is not None
    assert entry.agendamento_id is None
    assert entry.status == QueueEntryStatus.WAITING

    db.refresh(booking)
    assert booking.status == ReservationStatus.IN_QUEUE

    # Idempotente: rodar novamente não deve duplicar a entrada (dedupe por booking_id).
    count_repetido = QueueEntryService(db).processar_reservas_do_dia()
    assert (
        db.query(QueueEntry).filter(QueueEntry.booking_id == booking.id).count() == 1
    )


def test_checkin_iniciar_concluir_avancam_core_booking_para_entrada_core_only(
    db, synced_catalog, cliente_exemplo
):
    """checkin/iniciar/concluir avançam CoreBooking.status para entrada core-only (booking_id preenchido)."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=71)

    entry = QueueEntry(
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        posicao=1,
        data=slot.date(),
        status=QueueEntryStatus.WAITING,
        mesmo_dia=1,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    service = QueueEntryService(db)
    entry = service.aprovar_com_horario(entry.id, slot)
    assert entry.booking_id is not None
    assert entry.agendamento_id is None
    booking_id = entry.booking_id

    entry = service.checkin(entry.id)
    assert entry.status == QueueEntryStatus.CHECKED_IN
    booking = db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
    assert booking.status == ReservationStatus.CHECKED_IN

    entry = service.iniciar(entry.id)
    assert entry.status == QueueEntryStatus.IN_SERVICE
    db.refresh(booking)
    assert booking.status == ReservationStatus.IN_SERVICE

    entry = service.concluir(entry.id)
    assert entry.status == QueueEntryStatus.COMPLETED
    db.refresh(booking)
    assert booking.status == ReservationStatus.COMPLETED


def test_checkin_iniciar_mantem_legado_quando_sem_booking_id(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """Entrada legado pura (agendamento_id, sem booking_id) continua atualizando só Agendamento."""
    from app.models.agendamento import Agendamento, StatusPagamento
    from app.utils.service_image_precos import resolver_precos_imagem

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    agendamento = Agendamento(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=datetime.now() + timedelta(days=72),
        status=ReservationStatus.IN_QUEUE,
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

    entry = QueueEntry(
        agendamento_id=agendamento.id,
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        posicao=1,
        data=agendamento.data_hora.date(),
        status=QueueEntryStatus.WAITING,
        mesmo_dia=0,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    service = QueueEntryService(db)
    entry = service.checkin(entry.id)
    db.refresh(agendamento)
    assert agendamento.status == ReservationStatus.CHECKED_IN

    entry = service.iniciar(entry.id)
    db.refresh(agendamento)
    assert agendamento.status == ReservationStatus.IN_SERVICE


def test_fila_aprovar_fila_seta_booking_id(db, synced_catalog, cliente_exemplo):
    """FilaService.aprovar_fila vincula fila.booking_id ao booking core criado."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=73)

    fila = Fila(
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        data=slot.date(),
        posicao=1,
        status=StatusFila.WAITING,
        observacoes="fila r4-f5",
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)

    aprovada = FilaService(db).aprovar_fila(fila.id, FilaAprovarRequest(data_hora=slot))

    assert aprovada.status == StatusFila.APPROVED
    assert aprovada.agendamento_id is None
    assert aprovada.booking_id is not None

    booking = db.query(CoreBooking).filter(CoreBooking.id == aprovada.booking_id).first()
    assert booking is not None
    assert booking.customer_id == cliente_exemplo.id
