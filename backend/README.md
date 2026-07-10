# TrançaPro Backend - MVP

## 🚀 Início Rápido

### 1. Instalar dependências

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Executar aplicação

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`

### 3. Documentação

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📋 Endpoints Disponíveis

### Tranças
- `GET /trancas` - Lista tranças ativas
- `POST /trancas` - Cria trança
- `GET /trancas/{id}` - Obtém trança
- `PUT /trancas/{id}` - Atualiza trança

### Agendamentos
- `GET /agenda/disponibilidade?data={datetime}&tranca_id={id}` - Horários disponíveis
- `POST /agenda/agendamentos` - Cria agendamento
- `GET /agenda/agendamentos` - Lista agendamentos
- `GET /agenda/agendamentos/{id}` - Obtém agendamento
- `PUT /agenda/agendamentos/{id}` - Atualiza agendamento
- `DELETE /agenda/agendamentos/{id}` - Cancela agendamento

### Pagamentos
- `POST /pagamentos/sinal` - Confirma pagamento do sinal (mock)

### Fila Virtual
- `POST /fila/entrar` - Entra na fila
- `GET /fila/{date}` - Consulta fila do dia

### Financeiro
- `GET /financeiro/resumo?inicio={datetime}&fim={datetime}` - Resumo financeiro
- `POST /financeiro/saida` - Registra saída manual

### Webhook
- `POST /webhook/whatsapp` - Recebe mensagem WhatsApp (mock)

## 🗄️ Banco de Dados

O banco SQLite é criado automaticamente na primeira execução em `./trancapro.db`

Para recriar o banco:
```bash
python -c "from app.db.init_db import init_db; init_db()"
```

## 📝 Variáveis de Ambiente

Crie um arquivo `.env` (opcional):

```env
DATABASE_URL=sqlite:///./trancapro.db
DEBUG=false
CORS_ORIGINS=["*"]
PIX_MOCK_ENABLED=true
WHATSAPP_WEBHOOK_ENABLED=true
```

## 🧪 Testando a API

### Exemplo: Criar trança

```bash
curl -X POST "http://localhost:8000/trancas" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Box Braids",
    "descricao": "Tranças box braids clássicas",
    "duracao_minutos": 180,
    "valor_total": 150.00,
    "valor_sinal": 50.00,
    "imagens": ["https://exemplo.com/imagem.jpg"],
    "ativo": true
  }'
```

### Exemplo: Consultar disponibilidade

```bash
curl "http://localhost:8000/agenda/disponibilidade?data=2024-12-25T10:00:00&tranca_id=1"
```

### Exemplo: Criar agendamento

```bash
curl -X POST "http://localhost:8000/agenda/agendamentos" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "tranca_id": 1,
    "data_hora": "2024-12-25T10:00:00",
    "observacoes": "Cliente prefere cabelo limpo"
  }'
```

## 📚 Estrutura do Projeto

```
app/
├── main.py              # Aplicação FastAPI
├── models/              # Models SQLAlchemy
├── schemas/             # Schemas Pydantic
├── routers/             # Endpoints da API
├── services/            # Lógica de negócio
├── db/                  # Configuração do banco
└── core/                # Configurações e utilitários
```

## ✅ Regras de Negócio Implementadas

- ✅ Horários só aparecem se disponíveis
- ✅ Agendamento só confirma após sinal_pago = true
- ✅ Fila ativa bloqueia novos horários
- ✅ Toda entrada financeira é registrada automaticamente
- ✅ Validações centralizadas nos services

## 🔄 Próximos Passos

- [ ] Adicionar autenticação JWT
- [ ] Implementar testes automatizados
- [ ] Adicionar logging estruturado
- [ ] Migrar para PostgreSQL em produção
- [ ] Integrar Pix real
- [ ] Integrar WhatsApp real

