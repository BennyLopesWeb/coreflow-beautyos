"""
R4-F8 — DROP físico de ``agendamentos`` — ADR-024 sunset / RFC-003 M11+.

Sucede ``test_r4_f7_fk_decouple.py`` (decouple físico das últimas FKs
apontando para ``agendamentos``). R4-F7 deixou o campo livre — nenhuma
tabela mantém constraint física contra ``agendamentos`` — e R4-F8 executa
o DROP físico propriamente dito:

- ``agendamentos`` é removida via
  ``alembic/versions/cf016_r4_f8_drop_agendamentos.py`` (produção) e
  ``migrate_schema.py._migrar_r4_f8_drop_agendamentos`` (SQLite legado).
- ``Agendamento`` deixou de ser um model SQLAlchemy mapeado (não herda
  mais ``Base``) — ``create_all`` não a recria nunca mais.
- Todo código de produção que ainda consultava ``Agendamento`` foi
  reescrito para no-op (``NotFoundError``/lista vazia) ou para consultar
  ``CoreBooking`` equivalente.

Prova que:

- APP_VERSION == 2.11.0-r4-f8.
- A tabela ``agendamentos`` não existe mais no schema (via
  ``sa.inspect(...).get_table_names()``).
- ``Agendamento`` não é uma classe mapeada (``sa.inspect(Agendamento)``
  levanta erro / não está em ``Base.registry``).
- ``POST /v1/bookings`` continua funcionando normalmente (core-only).
- Pagamentos via ``booking_id`` continuam funcionando
  (``PaymentReservationService.confirmar_deposito_por_booking`` +
  ``GET /v1/payments?booking_id=``).
- ``AgendamentoService``/``ReservationService`` (leitura legado) são
  no-ops seguros (não levantam erro de "tabela não existe" — a
  aplicação não tenta mais consultar a tabela removida).
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
import sqlalchemy as sa

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.agendamento import Agendamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.services.agendamento_service import AgendamentoService
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


def test_app_version_r4_f8():
    """APP_VERSION avançou de R4-F8 (pin exato relaxado em R4-F9+; ver test_app_version_r4_f9)."""
    assert settings.APP_VERSION.startswith("2.")


def test_tabela_agendamentos_nao_existe_no_schema(db):
    """
    A tabela ``agendamentos`` não existe mais no schema criado a partir
    dos models atuais (``Base.metadata.create_all``) — equivalente ao que
    a migration ``cf016_r4_f8_drop_agendamentos`` garante em bancos reais.
    """
    inspector = sa.inspect(db.get_bind())
    assert "agendamentos" not in inspector.get_table_names()


def test_agendamento_nao_e_mais_model_mapeado():
    """
    ``Agendamento`` deixou de ser uma classe SQLAlchemy mapeada — não tem
    mais ``__tablename__``/``Base`` — consultá-la via ``session.query``
    levanta erro imediatamente (classe não mapeada), em vez de tentar
    acessar a tabela removida.
    """
    assert not hasattr(Agendamento, "__tablename__")
    assert not hasattr(Agendamento, "__table__")


def test_query_agendamento_levanta_erro_classe_nao_mapeada(db):
    """
    ``db.query(Agendamento)`` levanta erro (classe não mapeada) — nenhum
    call-site de produção deve mais fazer essa chamada (todos foram
    migrados/no-op nesta release).
    """
    with pytest.raises(Exception):
        db.query(Agendamento).count()


def test_criar_booking_v1_continua_funcionando(
    client, synced_catalog, cliente_exemplo, db, booking_headers
):
    """POST /v1/bookings continua criando CoreBooking normalmente após o DROP."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=200)

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
    body = response.json()
    assert body["legacy_agendamento_id"] is None

    row = db.query(CoreBooking).filter(CoreBooking.id == body["id"]).first()
    assert row is not None
    assert row.legacy_agendamento_id is None


def test_confirmar_deposito_por_booking_continua_funcionando(
    db, default_company, cliente_exemplo, synced_catalog
):
    """confirmar_deposito_por_booking cria Payment vinculado por booking_id (sem Agendamento)."""
    from app.modules.booking.application.commands.create_booking import (
        CreateBookingCommand,
        CreateBookingHandler,
    )

    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=201)

    result = CreateBookingHandler(db).execute(
        CreateBookingCommand(
            customer_id=cliente_exemplo.id,
            catalog_id=catalog.id,
            offering_id=offering.id,
            scheduled_at=slot,
            company_id=default_company.id,
        )
    )
    booking_id = result.booking.id

    atualizado = PaymentReservationService(db).confirmar_deposito_por_booking(booking_id)
    assert atualizado.deposit_paid is True

    pag = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    assert pag is not None
    assert pag.agendamento_id is None
    assert pag.status == PaymentStatus.PAID


def test_v1_payments_por_booking_id_continua_funcionando(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers
):
    """GET /v1/payments?booking_id= retorna pagamentos do booking core (sem tabela agendamentos)."""
    catalog, offering = synced_catalog
    slot = _slot_for_day(db, catalog, offering, days_ahead=202)

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
    booking_id = response.json()["id"]

    PaymentReservationService(db).confirmar_deposito_por_booking(booking_id)

    payments_resp = client.get(
        "/v1/payments",
        params={"booking_id": booking_id},
        headers=admin_headers,
    )
    assert payments_resp.status_code == 200
    data = payments_resp.json()
    assert len(data) >= 1
    assert data[0]["booking_id"] == booking_id


def test_agendamento_service_leitura_no_op(db):
    """AgendamentoService (leitura legado) é no-op seguro — nunca tenta consultar a tabela removida."""
    service = AgendamentoService(db)
    assert service.listar_agendamentos() == []
    assert service.buscar_por_id(1) is None
    with pytest.raises(NotFoundError):
        service.obter_agendamento(1)


def test_reservation_service_leitura_no_op(db):
    """ReservationService (leitura legado) é no-op seguro — nunca tenta consultar a tabela removida."""
    service = ReservationService(db)
    assert service.listar() == []
    with pytest.raises(NotFoundError):
        service.obter(1)
