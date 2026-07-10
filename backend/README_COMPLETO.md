# 📚 Documentação Completa - TrançaPro Backend

## 🎯 Visão Geral

Backend completo em FastAPI para sistema de agendamento e CRM de trancista.

**Status**: ✅ MVP Completo e Funcional

---

## 🚀 Início Rápido

### 1. Instalar Dependências
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Ambiente (Opcional)
```bash
cp .env.example .env
# Edite .env com suas configurações
```

### 3. Executar Aplicação
```bash
uvicorn app.main:app --reload
```

### 4. Acessar Documentação
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── main.py              # Aplicação FastAPI
│   ├── models/              # Models SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   ├── routers/             # Endpoints da API
│   ├── services/            # Lógica de negócio
│   ├── db/                  # Configuração do banco
│   └── core/                # Configurações e utilitários
├── tests/                   # Testes automatizados
├── scripts/                 # Scripts utilitários
├── requirements.txt         # Dependências
├── pytest.ini              # Configuração de testes
└── .env.example            # Exemplo de variáveis de ambiente
```

---

## 🔌 Endpoints Disponíveis

### Tranças
- `GET /trancas` - Lista tranças ativas
- `POST /trancas` - Cria trança
- `GET /trancas/{id}` - Obtém trança
- `PUT /trancas/{id}` - Atualiza trança

### Clientes
- `GET /clientes` - Lista clientes
- `POST /clientes` - Cria cliente
- `GET /clientes/{id}` - Obtém cliente
- `PUT /clientes/{id}` - Atualiza cliente

### Agendamentos
- `GET /agenda/disponibilidade` - Horários disponíveis
- `POST /agenda/agendamentos` - Cria agendamento
- `GET /agenda/agendamentos` - Lista agendamentos
- `GET /agenda/agendamentos/{id}` - Obtém agendamento
- `PUT /agenda/agendamentos/{id}` - Atualiza agendamento
- `DELETE /agenda/agendamentos/{id}` - Cancela agendamento

### Pagamentos
- `POST /pagamentos/sinal` - Confirma pagamento do sinal (mock)

### Fila Virtual
- `POST /fila/entrar` - Entra na fila
- `GET /fila/{date}` - Consulta fila

### Financeiro
- `GET /financeiro/resumo` - Resumo financeiro
- `POST /financeiro/saida` - Registra saída

### Webhook
- `POST /webhook/whatsapp` - Webhook WhatsApp (mock)

---

## 🧪 Testes

### Executar Testes
```bash
# Todos os testes
pytest

# Apenas unitários
pytest -m unit

# Apenas integração
pytest -m integration

# Com coverage
pytest --cov=app --cov-report=html
```

### Scripts
```bash
# Executar testes
./scripts/run_tests.sh

# Testar API manualmente
./scripts/test_api.sh
```

**Documentação**: Ver `tests/README.md`

---

## 📊 Logging

O sistema possui logging estruturado configurado:

- **Nível DEBUG**: Em modo desenvolvimento
- **Nível INFO**: Operações normais
- **Nível WARNING**: Avisos
- **Nível ERROR**: Erros

Logs são exibidos no console durante a execução.

---

## ⚠️ Tratamento de Erros

O sistema possui tratamento centralizado de erros:

- **Exceções customizadas**: Retornam mensagens padronizadas
- **Validação**: Erros de validação do Pydantic
- **Erros genéricos**: Handler para erros não tratados
- **Logging**: Todos os erros são logados

---

## 🗄️ Banco de Dados

### SQLite (MVP)
- Banco criado automaticamente em `./trancapro.db`
- Tabelas criadas na primeira execução

### Migração para PostgreSQL
1. Altere `DATABASE_URL` no `.env`
2. Instale `psycopg2-binary` no `requirements.txt`
3. Execute novamente (tabelas serão criadas)

---

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env`:

```env
DATABASE_URL=sqlite:///./trancapro.db
DEBUG=true
CORS_ORIGINS=["*"]
PIX_MOCK_ENABLED=true
WHATSAPP_WEBHOOK_ENABLED=true
```

### Configurações Disponíveis

- `DATABASE_URL`: URL do banco de dados
- `DEBUG`: Modo debug (true/false)
- `CORS_ORIGINS`: Origens permitidas para CORS
- `PIX_MOCK_ENABLED`: Habilitar mock de Pix
- `WHATSAPP_WEBHOOK_ENABLED`: Habilitar webhook WhatsApp

---

## 📝 Regras de Negócio

### Horários Disponíveis
- Verifica conflitos com agendamentos existentes
- Considera duração da trança
- Não permite agendamentos no passado
- Bloqueia horários se fila estiver ativa

### Agendamento
- Status inicial: `pendente`
- Só confirma após `sinal_pago = true`
- Cria entrada financeira automática ao confirmar sinal

### Fila Virtual
- Ativa quando dia está lotado
- Bloqueia novos agendamentos para o dia
- Posição calculada automaticamente

### Financeiro
- Toda entrada é registrada automaticamente
- Entradas automáticas ao confirmar sinal
- Saídas manuais
- Resumo calcula totais e saldo

---

## 🚀 Deploy

### Preparação
1. Configure variáveis de ambiente
2. Migre para PostgreSQL (recomendado)
3. Configure CORS para domínios específicos
4. Desabilite DEBUG em produção

### Executar
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 📚 Documentação Adicional

- `GUIA_USO_API.md` - Guia completo de uso da API
- `tests/README.md` - Documentação de testes
- `MELHORIAS_IMPLEMENTADAS.md` - Melhorias implementadas
- `STATUS_MELHORIAS.md` - Status das melhorias

---

## ✅ Checklist de Funcionalidades

- [x] CRUD de Tranças
- [x] CRUD de Clientes
- [x] Sistema de Agendamentos
- [x] Cálculo de Disponibilidade
- [x] Fila Virtual
- [x] Controle Financeiro
- [x] Pagamento Mock (Pix)
- [x] Webhook Mock (WhatsApp)
- [x] Testes Automatizados
- [x] Logging Estruturado
- [x] Tratamento de Erros

---

## 🎯 Próximos Passos

1. **Integrar Frontend** - React Web/React Native
2. **Adicionar Autenticação** - JWT quando necessário
3. **Integrações Reais** - Pix real, WhatsApp real
4. **Otimizações** - Cache, paginação, índices

---

**Status**: ✅ **PRONTO PARA USO**

