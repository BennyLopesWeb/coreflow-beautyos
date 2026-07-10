# 🧪 Testes - TrançaPro Backend

## 📋 Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
├── test_services/           # Testes unitários dos services
│   ├── test_tranca_service.py
│   ├── test_cliente_service.py
│   └── test_agendamento_service.py
└── test_integration/         # Testes de integração dos endpoints
    ├── test_trancas.py
    └── test_agendamentos.py
```

## 🚀 Como Executar

### Executar todos os testes
```bash
cd backend
pytest
```

### Executar apenas testes unitários
```bash
pytest -m unit
```

### Executar apenas testes de integração
```bash
pytest -m integration
```

### Executar com coverage
```bash
pytest --cov=app --cov-report=html
```

### Executar um arquivo específico
```bash
pytest tests/test_services/test_tranca_service.py
```

### Executar um teste específico
```bash
pytest tests/test_services/test_tranca_service.py::test_criar_tranca_valida
```

## 📊 Cobertura

Após executar os testes com coverage, abra `htmlcov/index.html` no navegador para ver o relatório detalhado.

## 🎯 Tipos de Testes

### Testes Unitários (`@pytest.mark.unit`)
- Testam lógica de negócio isolada
- Services testados independentemente
- Banco de dados em memória (SQLite)

### Testes de Integração (`@pytest.mark.integration`)
- Testam endpoints completos
- Usam FastAPI TestClient
- Verificam fluxo completo da requisição

## 🔧 Fixtures Disponíveis

- `db`: Sessão de banco de dados de teste
- `client`: Cliente HTTP para testes (FastAPI TestClient)
- `cliente_exemplo`: Cliente pré-criado para testes
- `tranca_exemplo`: Trança pré-criada para testes

## 📝 Exemplo de Teste

```python
@pytest.mark.unit
def test_criar_tranca_valida(db):
    """Testa criação de trança válida"""
    service = TrancaService(db)
    
    tranca_data = TrancaCreate(
        nome="Trança Teste",
        duracao_minutos=120,
        valor_total=Decimal("100.00"),
        valor_sinal=Decimal("30.00"),
        imagens=[],
        ativo=True
    )
    
    tranca = service.criar_tranca(tranca_data)
    
    assert tranca.id is not None
    assert tranca.nome == "Trança Teste"
```

## ✅ Checklist de Cobertura

- [x] Testes unitários dos services principais
- [x] Testes de integração dos endpoints principais
- [ ] Testes de edge cases
- [ ] Testes de performance
- [ ] Testes de segurança

## 🎯 Próximos Passos

1. Adicionar mais testes unitários
2. Adicionar testes de edge cases
3. Adicionar testes de performance
4. Configurar CI/CD com testes automáticos

