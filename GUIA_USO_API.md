# 📚 Guia de Uso da API - TrançaPro

## 🚀 Início Rápido

### 1. Iniciar o Servidor
```bash
cd backend
uvicorn app.main:app --reload
```

A API estará disponível em: `http://localhost:8000`

### 2. Acessar Documentação
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📋 Endpoints Principais

### 🎨 Tranças

#### Listar Tranças Ativas
```bash
GET /trancas
```

**Resposta:**
```json
[
  {
    "id": 1,
    "nome": "Box Braids",
    "descricao": "Tranças box braids clássicas",
    "duracao_minutos": 180,
    "valor_total": "150.00",
    "valor_sinal": "50.00",
    "imagens": ["https://exemplo.com/img.jpg"],
    "ativo": true
  }
]
```

#### Criar Trança
```bash
POST /trancas
Content-Type: application/json

{
  "nome": "Box Braids",
  "descricao": "Tranças box braids clássicas",
  "duracao_minutos": 180,
  "valor_total": "150.00",
  "valor_sinal": "50.00",
  "imagens": ["https://exemplo.com/img.jpg"],
  "ativo": true
}
```

---

### 👥 Clientes

#### Criar Cliente
```bash
POST /clientes
Content-Type: application/json

{
  "nome": "Maria Silva",
  "telefone": "11999999999",
  "email": "maria@email.com"
}
```

#### Listar Clientes
```bash
GET /clientes
```

---

### 📅 Agendamentos

#### Consultar Disponibilidade
```bash
GET /agenda/disponibilidade?data=2024-12-25T10:00:00&tranca_id=1
```

**Resposta:**
```json
{
  "data": "2024-12-25T10:00:00",
  "tranca_id": 1,
  "horarios": [
    {
      "horario": "2024-12-25T08:00:00",
      "disponivel": true
    },
    {
      "horario": "2024-12-25T08:30:00",
      "disponivel": false
    }
  ]
}
```

#### Criar Agendamento
```bash
POST /agenda/agendamentos
Content-Type: application/json

{
  "cliente_id": 1,
  "tranca_id": 1,
  "data_hora": "2024-12-25T10:00:00",
  "observacoes": "Cliente prefere cabelo limpo"
}
```

**Resposta:**
```json
{
  "id": 1,
  "cliente_id": 1,
  "tranca_id": 1,
  "data_hora": "2024-12-25T10:00:00",
  "sinal_pago": false,
  "status": "pendente",
  "observacoes": "Cliente prefere cabelo limpo"
}
```

---

### 💰 Pagamentos

#### Confirmar Pagamento do Sinal
```bash
POST /pagamentos/sinal
Content-Type: application/json

{
  "agendamento_id": 1,
  "valor": 50.00
}
```

**Resposta:**
```json
{
  "agendamento_id": 1,
  "sinal_pago": true,
  "mensagem": "Pagamento do sinal confirmado com sucesso"
}
```

---

### 📊 Financeiro

#### Resumo Financeiro
```bash
GET /financeiro/resumo?inicio=2024-12-01T00:00:00&fim=2024-12-31T23:59:59
```

**Resposta:**
```json
{
  "inicio": "2024-12-01T00:00:00",
  "fim": "2024-12-31T23:59:59",
  "total_entradas": "500.00",
  "total_saidas": "100.00",
  "saldo": "400.00",
  "movimentos": [...]
}
```

#### Registrar Saída
```bash
POST /financeiro/saida
Content-Type: application/json

{
  "descricao": "Compra de material",
  "valor": "50.00",
  "data": "2024-12-15T10:00:00"
}
```

---

### 🎯 Fila Virtual

#### Entrar na Fila
```bash
POST /fila/entrar
Content-Type: application/json

{
  "agendamento_id": 1
}
```

#### Consultar Fila
```bash
GET /fila/2024-12-25
```

---

## 🧪 Testando a API

### Usando cURL

#### Exemplo Completo
```bash
# 1. Criar trança
curl -X POST "http://localhost:8000/trancas" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Box Braids",
    "descricao": "Tranças box braids",
    "duracao_minutos": 180,
    "valor_total": "150.00",
    "valor_sinal": "50.00",
    "imagens": [],
    "ativo": true
  }'

# 2. Criar cliente
curl -X POST "http://localhost:8000/clientes" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Maria Silva",
    "telefone": "11999999999",
    "email": "maria@email.com"
  }'

# 3. Consultar disponibilidade
curl "http://localhost:8000/agenda/disponibilidade?data=2024-12-25T10:00:00&tranca_id=1"

# 4. Criar agendamento
curl -X POST "http://localhost:8000/agenda/agendamentos" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "tranca_id": 1,
    "data_hora": "2024-12-25T10:00:00"
  }'

# 5. Confirmar pagamento
curl -X POST "http://localhost:8000/pagamentos/sinal" \
  -H "Content-Type: application/json" \
  -d '{
    "agendamento_id": 1,
    "valor": 50.00
  }'
```

### Usando Script Automatizado
```bash
cd backend/scripts
chmod +x test_api.sh
./test_api.sh
```

---

## 🔍 Verificando Status

### Health Check
```bash
GET /health
```

**Resposta:**
```json
{
  "status": "healthy"
}
```

### Root
```bash
GET /
```

**Resposta:**
```json
{
  "message": "TrançaPro",
  "version": "1.0.0",
  "docs": "/docs",
  "status": "ok"
}
```

---

## ⚠️ Tratamento de Erros

### Erro de Validação
```json
{
  "error": true,
  "message": "Erro de validação",
  "errors": [
    {
      "loc": ["body", "valor_sinal"],
      "msg": "Valor do sinal não pode ser maior que o valor total",
      "type": "value_error"
    }
  ],
  "path": "/trancas"
}
```

### Recurso Não Encontrado
```json
{
  "error": true,
  "message": "Trança não encontrado: 999",
  "path": "/trancas/999"
}
```

### Erro de Regra de Negócio
```json
{
  "error": true,
  "message": "Horário não está disponível",
  "path": "/agenda/agendamentos"
}
```

---

## 📝 Notas Importantes

1. **Datas**: Use formato ISO 8601: `YYYY-MM-DDTHH:MM:SS`
2. **Valores**: Use strings para valores decimais: `"150.00"`
3. **IDs**: Retornados como inteiros
4. **Status**: Agendamentos começam como `pendente`, mudam para `confirmado` após pagamento

---

## 🚀 Próximos Passos

1. **Integrar com Frontend** - React Web/React Native
2. **Adicionar Autenticação** - Quando necessário
3. **Configurar Produção** - PostgreSQL, variáveis de ambiente
4. **Monitoramento** - Logs, métricas, alertas

---

**Documentação Completa**: http://localhost:8000/docs

