"""
R4-F4 - Hard sunset de Agendamento (Option A, sem DROP TABLE) - ADR-024 / RFC-003 M8.

Sucede test_r4_f3_dual_write_removed.py (que removeu o codigo do
dual-write outbound, mas manteve AgendamentoService.criar_agendamento
funcional e FilaService.aprovar_fila escrevendo em agendamentos).
R4-F4 vai alem: nenhum caminho de escrita de producao pode mais inserir
linhas em agendamentos - core_bookings passa a ser SoT tambem para
disponibilidade e processamento da fila do dia. Prova que:

- APP_VERSION == 2.7.0-r4-f4.
- AgendamentoService.criar_agendamento levanta BusinessRuleError
  incondicionalmente, apontando para POST /v1/bookings.
- POST /v1/bookings nao incrementa a contagem de agendamentos.
- DisponibilidadeService marca slot como indisponivel quando existe
  core_booking ativo ocupando-o (sem depender de linha em agendamentos).
- FilaService.aprovar_fila nao cria Agendamento - delega a
  CreateBookingHandler (mesmo padrao de
  QueueEntryService.aprovar_com_horario desde R4-F3).
- agendamentos permanece disponivel para leitura historica (listar/obter).

A tabela agendamentos nao e removida nesta sprint (fora de escopo - ver
docs/sprints/R4-F4.md); o DROP fisico fica para R4-F5.
"""
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessRuleError
from app.models.agendamento import Agendamento
from app.modules.booking.domain.models import CoreBooking
from app.schemas.agendamento import AgendamentoCreate
from app.schemas.fila import FilaAprovarRequest
from app.services.agendamento_service import AgendamentoService
from app.services.disponibilidade_service import DisponibilidadeService
from app.services.fila_service import FilaService


def _slot_for_day(db, catalog, offering, days_ahead: int) -> datetime:
    """
    Retorna primeiro horario disponivel N dias a frente.

    Args:
        db: Sessao SQLAlchemy de teste.
        catalog: Fixture CoreCatalog sincronizado.
        offering: Fixture CoreOffering sincronizado.
        days_ahead: Deslocamento em dias para o slot candidato.

    Returns:
        datetime do primeiro horario disponivel encontrado.
    """
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=days_ahead),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    return next(h for h in horarios if h.disponivel).horario


def _create_booking(client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead: int) -> dict:
    """
    Cria booking via POST /v1/bookings - sempre core-only (R4-F3/R4-F4).

    Args:
        client: TestClient FastAPI.
        db: Sessao SQLAlchemy de teste.
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


def test_app_version_r4_f4():
    """APP_VERSION avançou de R4-F4 (pin exato relaxado em R4-F5+; ver test_app_version_r4_f5)."""
    assert settings.APP_VERSION.startswith("2.")


def test_criar_agendamento_sempre_falha(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """R4-F4 - AgendamentoService.criar_agendamento levanta BusinessRuleError apontando /v1/bookings."""
    data_hora = datetime.now() + timedelta(days=30)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora,
    )

    with pytest.raises(BusinessRuleError, match="v1/bookings"):
        AgendamentoService(db).criar_agendamento(agendamento_data)


def test_criar_booking_v1_nao_cria_agendamento(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """POST /v1/bookings nao incrementa a contagem de Agendamento (core-only)."""
    before = db.query(Agendamento).count()

    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=60
    )

    assert booking["legacy_agendamento_id"] is None
    assert db.query(Agendamento).count() == before

    row = db.query(CoreBooking).filter(CoreBooking.id == booking["id"]).first()
    assert row is not None
    assert row.legacy_agendamento_id is None


def test_disponibilidade_marca_slot_ocupado_por_core_booking(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """DisponibilidadeService usa core_bookings como SoT - slot some sem linha em agendamentos."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=61)

    before = db.query(Agendamento).count()

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

    # Nenhuma linha nova em agendamentos - a checagem abaixo nao pode depender dela.
    assert db.query(Agendamento).count() == before

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        slot, catalog.legacy_tranca_id, offering.legacy_service_image_id
    )
    ocupado = next(h for h in horarios if h.horario == slot)
    assert ocupado.disponivel is False


def test_disponibilidade_nao_ve_mais_agendamento_historico(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """
    DisponibilidadeService não bloqueia mais slot por Agendamento histórico
    (superado — R4-F7 removeu a leitura de compatibilidade sobre
    ``agendamentos`` em ``_slots_ocupados``; ``core_bookings`` é a única
    fonte de ocupação desde então).

    Documentava, até R4-F6, que a leitura de compatibilidade sobre
    ``Agendamento`` legado ainda bloqueava slots (candidata a remoção — ver
    docstring anterior de ``_slots_ocupados``); R4-F7 executou essa
    remoção (débito residual aceito e documentado em
    ``docs/sprints/R4-F7.md`` — reservas legado históricas ativas não
    bloqueiam mais a agenda, apenas ``core_bookings``).
    """
    from decimal import Decimal

    from app.models.agendamento import ReservationStatus, StatusPagamento
    from app.utils.service_image_precos import resolver_precos_imagem

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=62),
        tranca_exemplo.id,
        service_image_exemplo.id,
    )
    slot = next(h for h in horarios if h.disponivel).horario

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    agendamento = Agendamento(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=slot,
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

    horarios_depois = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=62),
        tranca_exemplo.id,
        service_image_exemplo.id,
    )
    ainda_disponivel = next(h for h in horarios_depois if h.horario == slot)
    assert ainda_disponivel.disponivel is True


def test_fila_aprovar_nao_cria_agendamento(db, synced_catalog, cliente_exemplo):
    """R4-F4 - FilaService.aprovar_fila delega a CreateBookingHandler, sem criar Agendamento."""
    from app.models.fila import Fila, StatusFila

    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=63)

    fila = Fila(
        cliente_id=cliente_exemplo.id,
        tranca_id=catalog.legacy_tranca_id,
        service_image_id=offering.legacy_service_image_id,
        data=slot.date(),
        posicao=1,
        status=StatusFila.WAITING,
        observacoes="fila r4-f4",
    )
    db.add(fila)
    db.commit()
    db.refresh(fila)

    before = db.query(Agendamento).count()

    aprovada = FilaService(db).aprovar_fila(fila.id, FilaAprovarRequest(data_hora=slot))

    assert aprovada.status == StatusFila.APPROVED
    assert aprovada.agendamento_id is None
    assert db.query(Agendamento).count() == before

    booking = (
        db.query(CoreBooking)
        .filter(
            CoreBooking.customer_id == cliente_exemplo.id,
            CoreBooking.catalog_id == catalog.id,
            CoreBooking.offering_id == offering.id,
        )
        .first()
    )
    assert booking is not None
    assert booking.legacy_agendamento_id is None


def test_agendamento_listar_obter_ainda_funcionam(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """Leitura historica (listar/obter) continua funcionando apos o hard sunset."""
    from decimal import Decimal

    from app.models.agendamento import ReservationStatus, StatusPagamento
    from app.utils.service_image_precos import resolver_precos_imagem

    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=64),
        tranca_exemplo.id,
        service_image_exemplo.id,
    )
    slot = next(h for h in horarios if h.disponivel).horario

    precos = resolver_precos_imagem(service_image_exemplo, tranca_exemplo)
    agendamento = Agendamento(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=slot,
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

    service = AgendamentoService(db)
    encontrado = service.obter_agendamento(agendamento.id)
    assert encontrado.id == agendamento.id

    todos = service.listar_agendamentos()
    assert any(a.id == agendamento.id for a in todos)


def test_confirmar_sinal_admin_booking_endpoint(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """R4-F4 - endpoint admin cheap-path aceita booking_id direto (sem Agendamento)."""
    booking = _create_booking(
        client, db, synced_catalog, cliente_exemplo, booking_headers, days_ahead=65
    )

    response = client.post(
        f"/admin/pagamentos/booking/{booking['id']}/confirmar-sinal",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == booking["id"]
    assert body["deposit_paid"] is True

    row = db.query(CoreBooking).filter(CoreBooking.id == booking["id"]).first()
    assert row.deposit_paid is True
