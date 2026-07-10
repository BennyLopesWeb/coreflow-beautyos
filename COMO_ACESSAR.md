# 🌐 Como Acessar a API - TrançaPro

## ✅ Você está vendo `{"status": "healthy"}`?

Isso significa que o servidor está funcionando! Você está acessando o endpoint `/health`.

---

## 📚 Para Ver a Documentação Interativa

### Opção 1: Swagger UI (Recomendado)
**Acesse**: http://localhost:8000/docs

Esta é a interface interativa onde você pode:
- Ver todos os endpoints
- Testar endpoints diretamente no navegador
- Ver exemplos de requisições e respostas
- Executar chamadas à API

### Opção 2: ReDoc
**Acesse**: http://localhost:8000/redoc

Documentação alternativa em formato ReDoc.

---

## 🔗 URLs Disponíveis

| URL | Descrição |
|-----|-----------|
| http://localhost:8000/ | Página inicial da API |
| http://localhost:8000/health | Health check (o que você está vendo) |
| http://localhost:8000/docs | **Swagger UI - Documentação Interativa** ⭐ |
| http://localhost:8000/redoc | ReDoc - Documentação alternativa |

---

## 🚀 Testando a API

### 1. Via Swagger UI (Mais Fácil)
1. Acesse: http://localhost:8000/docs
2. Clique em qualquer endpoint
3. Clique em "Try it out"
4. Preencha os dados
5. Clique em "Execute"
6. Veja a resposta

### 2. Via cURL (Terminal)
```bash
# Health check
curl http://localhost:8000/health

# Listar tranças
curl http://localhost:8000/trancas

# Criar trança
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
```

---

## 📝 Endpoints Principais

### Tranças
- `GET /trancas` - Lista tranças ativas
- `POST /trancas` - Cria trança

### Clientes
- `GET /clientes` - Lista clientes
- `POST /clientes` - Cria cliente

### Agendamentos
- `GET /agenda/disponibilidade` - Horários disponíveis
- `POST /agenda/agendamentos` - Cria agendamento

### Pagamentos
- `POST /pagamentos/sinal` - Confirma pagamento

### Financeiro
- `GET /financeiro/resumo` - Resumo financeiro

---

## ✅ Próximo Passo

**Acesse agora**: http://localhost:8000/docs

Esta é a interface completa onde você pode testar todos os endpoints!

