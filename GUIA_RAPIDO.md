# 🚀 Guia Rápido - Backend MVP

## ⚡ Início em 3 Passos

### 1. Instalar
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Executar
```bash
uvicorn app.main:app --reload
```

### 3. Testar
Acesse: http://localhost:8000/docs

---

## 📋 Fluxo Básico de Uso

### 1. Criar Cliente
```bash
POST /clientes
{
  "nome": "Maria Silva",
  "telefone": "11999999999",
  "email": "maria@email.com"
}
```

### 2. Criar Trança
```bash
POST /trancas
{
  "nome": "Box Braids",
  "descricao": "Tranças box braids",
  "duracao_minutos": 180,
  "valor_total": 150.00,
  "valor_sinal": 50.00,
  "imagens": ["https://exemplo.com/img.jpg"],
  "ativo": true
}
```

### 3. Consultar Disponibilidade
```bash
GET /agenda/disponibilidade?data=2024-12-25T10:00:00&tranca_id=1
```

### 4. Criar Agendamento
```bash
POST /agenda/agendamentos
{
  "cliente_id": 1,
  "tranca_id": 1,
  "data_hora": "2024-12-25T10:00:00",
  "observacoes": "Cliente prefere cabelo limpo"
}
```

### 5. Confirmar Pagamento do Sinal
```bash
POST /pagamentos/sinal
{
  "agendamento_id": 1,
  "valor": 50.00
}
```

### 6. Consultar Resumo Financeiro
```bash
GET /financeiro/resumo?inicio=2024-12-01T00:00:00&fim=2024-12-31T23:59:59
```

---

## 🎯 Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/trancas` | Lista tranças ativas |
| POST | `/trancas` | Cria trança |
| GET | `/agenda/disponibilidade` | Horários disponíveis |
| POST | `/agenda/agendamentos` | Cria agendamento |
| POST | `/pagamentos/sinal` | Confirma pagamento |
| POST | `/fila/entrar` | Entra na fila |
| GET | `/fila/{date}` | Consulta fila |
| GET | `/financeiro/resumo` | Resumo financeiro |
| POST | `/webhook/whatsapp` | Webhook WhatsApp |

---

## 📚 Documentação Completa

- **PLANO_IMPLEMENTACAO.md** - Plano detalhado
- **IMPLEMENTACAO_COMPLETA.md** - Checklist completo
- **RESUMO_IMPLEMENTACAO.md** - Resumo executivo
- **backend/README.md** - Documentação técnica

---

## ✅ Status

**Backend MVP 100% Implementado e Funcional**

