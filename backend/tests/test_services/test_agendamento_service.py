"""
Testes unitários do AgendamentoService.

R4-F4 (hard sunset / ADR-024 / RFC-003 M8): ``criar_agendamento`` foi
desativado — levanta ``BusinessRuleError`` incondicionalmente (ver
``test_criar_agendamento_desativado``). Os testes de ``confirmar_sinal``/
``aprovar_reserva`` (que operam sobre reservas legado já existentes, e
continuam suportados para histórico) passam a criar o ``Agendamento`` via
ORM direto em vez de ``criar_agendamento``.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.agendamento import Agendamento, ReservationStatus, StatusPagamento
from app.services.agendamento_service import AgendamentoService
from app.schemas.agendamento import AgendamentoCreate
from app.core.exceptions import BusinessRuleError
from app.utils.service_image_precos import calcular_sinal, resolver_precos_imagem


def _criar_agendamento_orm(db, cliente, tranca, service_image, data_hora: datetime) -> Agendamento:
    """
    Cria um ``Agendamento`` legado diretamente via ORM (sem passar por ``criar_agendamento``).

    Substitui a antiga criação via ``AgendamentoService.criar_agendamento``
    (desativada em R4-F4) — usado apenas para exercitar métodos que ainda
    operam sobre reservas históricas (``confirmar_sinal``/``aprovar_reserva``).

    Args:
        db: Sessão SQLAlchemy de teste.
        cliente: Fixture de cliente.
        tranca: Fixture de categoria (tranca).
        service_image: Fixture de modelo (service image).
        data_hora: Horário da reserva.

    Returns:
        Agendamento persistido, com ``valor_total``/``valor_sinal``/``valor_restante``
        resolvidos a partir do modelo.
    """
    precos = resolver_precos_imagem(service_image, tranca)
    agendamento = Agendamento(
        cliente_id=cliente.id,
        tranca_id=tranca.id,
        service_image_id=service_image.id,
        data_hora=data_hora,
        status=ReservationStatus.PENDING_PAYMENT,
        sinal_pago=False,
        valor_total=precos["valor_total"],
        percentual_sinal=service_image.percentual_sinal or Decimal("0.30"),
        valor_sinal=precos["valor_sinal"],
        valor_restante=precos["valor_restante"],
        status_pagamento=StatusPagamento.PENDING_PAYMENT,
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)
    return agendamento


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
def test_confirmar_sinal(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa confirmação de pagamento do sinal sobre reserva legado existente"""
    service = AgendamentoService(db)

    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)

    agendamento = _criar_agendamento_orm(
        db, cliente_exemplo, tranca_exemplo, service_image_exemplo, data_hora
    )

    # Confirma sinal
    agendamento_atualizado = service.confirmar_sinal(agendamento.id)

    assert agendamento_atualizado.sinal_pago is True
    assert agendamento_atualizado.status.value in ("pending_approval", "PENDING_APPROVAL")
    assert agendamento_atualizado.status_pagamento.value == "partially_paid"

    # Verifica entrada financeira criada
    from app.models.financeiro import Financeiro, TipoMovimento
    movimentos = db.query(Financeiro).filter(
        Financeiro.agendamento_id == agendamento.id
    ).all()

    assert len(movimentos) == 1
    assert movimentos[0].tipo == TipoMovimento.ENTRADA
    assert movimentos[0].valor == calcular_sinal(Decimal("150.00"))


@pytest.mark.unit
def test_aprovar_reserva(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa aprovação manual após pagamento do sinal sobre reserva legado existente"""
    service = AgendamentoService(db)

    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=11, minute=0, second=0, microsecond=0)

    agendamento = _criar_agendamento_orm(
        db, cliente_exemplo, tranca_exemplo, service_image_exemplo, data_hora
    )
    service.confirmar_sinal(agendamento.id)
    aprovado = service.aprovar_reserva(agendamento.id)

    assert aprovado.status.value in ("approved", "confirmado")
