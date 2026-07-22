"""
Testes unitários do AgendamentoService.

.. deprecated:: 2.11.0-r4-f8
    A tabela ``agendamentos`` foi removida via DROP físico (ADR-024
    sunset / RFC-003 M11+) — ``Agendamento`` deixou de ser um model
    SQLAlchemy mapeado (ver ``app/models/agendamento.py``). O service
    inteiro passou a ser um conjunto de no-ops: escrita (``criar_agendamento``)
    já estava desativada desde R4-F4 (hard sunset), e leitura
    (``confirmar_sinal``/``aprovar_reserva``/``listar_agendamentos``/
    ``obter_agendamento``) agora sempre retorna vazio ou levanta
    ``NotFoundError``, já que não há mais dados para consultar. Os testes
    abaixo cobrem esse comportamento — a criação direta de ``Agendamento``
    via ORM (usada antes desta release para exercitar reservas legado
    "existentes") não é mais possível.
"""
import pytest
from datetime import datetime, timedelta

from app.services.agendamento_service import AgendamentoService
from app.schemas.agendamento import AgendamentoCreate
from app.core.exceptions import BusinessRuleError, NotFoundError


@pytest.mark.unit
def test_criar_agendamento_desativado(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """R4-F4 — criar_agendamento levanta BusinessRuleError apontando para /v1/bookings."""
    service = AgendamentoService(db)

    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora,
        observacoes="Teste",
    )

    with pytest.raises(BusinessRuleError, match="v1/bookings"):
        service.criar_agendamento(agendamento_data)


@pytest.mark.unit
def test_criar_agendamento_desativado_mesmo_no_passado(
    db, cliente_exemplo, tranca_exemplo, service_image_exemplo
):
    """R4-F4 — criar_agendamento falha incondicionalmente, mesmo com data no passado."""
    service = AgendamentoService(db)

    data_passada = datetime.now() - timedelta(days=1)

    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_passada,
    )

    with pytest.raises(BusinessRuleError):
        service.criar_agendamento(agendamento_data)


@pytest.mark.unit
def test_listar_agendamentos_sempre_vazio(db):
    """R4-F8 — listar_agendamentos sempre retorna lista vazia (tabela removida)."""
    assert AgendamentoService(db).listar_agendamentos() == []


@pytest.mark.unit
def test_obter_agendamento_sempre_not_found(db):
    """R4-F8 — obter_agendamento sempre levanta NotFoundError (tabela removida)."""
    with pytest.raises(NotFoundError):
        AgendamentoService(db).obter_agendamento(1)


@pytest.mark.unit
def test_confirmar_sinal_sempre_not_found(db):
    """R4-F8 — confirmar_sinal delega a obter_agendamento, sempre NotFoundError."""
    with pytest.raises(NotFoundError):
        AgendamentoService(db).confirmar_sinal(1)


@pytest.mark.unit
def test_aprovar_reserva_sempre_not_found(db):
    """R4-F8 — aprovar_reserva delega a obter_agendamento, sempre NotFoundError."""
    with pytest.raises(NotFoundError):
        AgendamentoService(db).aprovar_reserva(1)


@pytest.mark.unit
def test_cancelar_agendamento_sempre_not_found(db):
    """R4-F8 — cancelar_agendamento delega a obter_agendamento, sempre NotFoundError."""
    with pytest.raises(NotFoundError):
        AgendamentoService(db).cancelar_agendamento(1)
