"""
Testes unitários do AgendamentoService
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.services.agendamento_service import AgendamentoService
from app.schemas.agendamento import AgendamentoCreate
from app.core.exceptions import ValidationError, BusinessRuleError
from app.utils.service_image_precos import calcular_sinal


@pytest.mark.unit
def test_criar_agendamento_valido(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa criação de agendamento válido"""
    service = AgendamentoService(db)
    
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)
    
    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora,
        observacoes="Teste"
    )
    
    agendamento = service.criar_agendamento(agendamento_data)
    
    assert agendamento.id is not None
    assert agendamento.cliente_id == cliente_exemplo.id
    assert agendamento.tranca_id == tranca_exemplo.id
    assert agendamento.service_image_id == service_image_exemplo.id
    assert agendamento.sinal_pago is False
    assert agendamento.valor_total == Decimal("150.00")
    assert agendamento.valor_sinal == Decimal("45.00")
    assert agendamento.valor_restante == Decimal("105.00")
    assert agendamento.status_pagamento.value == "pending_payment"


@pytest.mark.unit
def test_criar_agendamento_passado(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa validação: não permite agendamento no passado"""
    service = AgendamentoService(db)
    
    data_passada = datetime.now() - timedelta(days=1)
    
    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_passada
    )
    
    with pytest.raises(ValidationError):
        service.criar_agendamento(agendamento_data)


@pytest.mark.unit
def test_confirmar_sinal(db, cliente_exemplo, tranca_exemplo, service_image_exemplo):
    """Testa confirmação de pagamento do sinal"""
    service = AgendamentoService(db)
    
    # Cria agendamento
    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=10, minute=0, second=0, microsecond=0)
    
    agendamento_data = AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora
    )
    agendamento = service.criar_agendamento(agendamento_data)
    
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
    """Testa aprovação manual após pagamento do sinal"""
    service = AgendamentoService(db)

    data_hora = datetime.now() + timedelta(days=1)
    data_hora = data_hora.replace(hour=11, minute=0, second=0, microsecond=0)

    agendamento = service.criar_agendamento(AgendamentoCreate(
        cliente_id=cliente_exemplo.id,
        tranca_id=tranca_exemplo.id,
        service_image_id=service_image_exemplo.id,
        data_hora=data_hora,
    ))
    service.confirmar_sinal(agendamento.id)
    aprovado = service.aprovar_reserva(agendamento.id)

    assert aprovado.status.value in ("approved", "confirmado")

