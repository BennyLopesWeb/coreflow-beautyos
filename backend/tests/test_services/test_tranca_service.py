"""
Testes unitários do TrancaService (categorias)
"""
import pytest
from app.services.tranca_service import TrancaService
from app.schemas.tranca import TrancaCreate, TrancaUpdate
from app.core.exceptions import ValidationError


@pytest.mark.unit
def test_criar_categoria_valida(db):
    """Categoria é criada sem preço ou duração."""
    service = TrancaService(db)
    tranca = service.criar_tranca(
        TrancaCreate(nome="Box Braids", descricao="Estilo box", ativo=True)
    )
    assert tranca.id is not None
    assert tranca.nome == "Box Braids"
    assert tranca.valor_total is None or tranca.valor_total == 0


@pytest.mark.unit
def test_criar_categoria_nome_duplicado(db):
    """Não permite duas categorias com mesmo nome."""
    service = TrancaService(db)
    service.criar_tranca(TrancaCreate(nome="Box Braids", ativo=True))
    with pytest.raises(ValidationError):
        service.criar_tranca(TrancaCreate(nome="Box Braids", ativo=True))


@pytest.mark.unit
def test_atualizar_categoria(db):
    """Atualiza nome e descrição da categoria."""
    service = TrancaService(db)
    tranca = service.criar_tranca(TrancaCreate(nome="Fulani", ativo=True))
    atualizada = service.atualizar_tranca(
        tranca.id,
        TrancaUpdate(nome="Fulani Braids", descricao="Trança fulani"),
    )
    assert atualizada.nome == "Fulani Braids"
    assert atualizada.descricao == "Trança fulani"
