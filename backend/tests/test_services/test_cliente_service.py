"""
Testes unitários do ClienteService
"""
import pytest
from app.services.cliente_service import ClienteService
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.core.exceptions import ConflictError, NotFoundError


@pytest.mark.unit
def test_criar_cliente_valido(db):
    """Testa criação de cliente válido"""
    service = ClienteService(db)
    
    cliente_data = ClienteCreate(
        nome="João Silva",
        telefone="11988888888",
        email="joao@email.com"
    )
    
    cliente = service.criar_cliente(cliente_data)
    
    assert cliente.id is not None
    assert cliente.nome == "João Silva"
    assert cliente.telefone == "11988888888"


@pytest.mark.unit
def test_criar_cliente_telefone_duplicado(db, cliente_exemplo):
    """Testa validação: telefone deve ser único"""
    service = ClienteService(db)
    
    cliente_data = ClienteCreate(
        nome="Outro Cliente",
        telefone="11999999999",  # Mesmo telefone
        email="outro@email.com"
    )
    
    with pytest.raises(ConflictError):
        service.criar_cliente(cliente_data)


@pytest.mark.unit
def test_buscar_cliente_por_telefone(db, cliente_exemplo):
    """Testa busca de cliente por telefone"""
    service = ClienteService(db)
    
    cliente = service.buscar_por_telefone("11999999999")
    
    assert cliente is not None
    assert cliente.nome == "Maria Silva"


@pytest.mark.unit
def test_atualizar_cliente(db, cliente_exemplo):
    """Testa atualização de cliente"""
    service = ClienteService(db)
    
    update_data = ClienteUpdate(nome="Maria Santos")
    cliente_atualizado = service.atualizar_cliente(cliente_exemplo.id, update_data)
    
    assert cliente_atualizado.nome == "Maria Santos"
    assert cliente_atualizado.telefone == cliente_exemplo.telefone

