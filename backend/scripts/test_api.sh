#!/bin/bash

# Script para testar a API manualmente
# Executa testes básicos dos endpoints

BASE_URL="http://localhost:8000"

echo "🧪 Testando API TrançaPro"
echo "=========================="
echo ""

# Health check
echo "1. Health Check..."
curl -s "$BASE_URL/health" | jq .
echo ""

# Listar tranças
echo "2. Listar Tranças..."
curl -s "$BASE_URL/trancas" | jq .
echo ""

# Criar trança
echo "3. Criar Trança..."
TRANCA_RESPONSE=$(curl -s -X POST "$BASE_URL/trancas" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Box Braids",
    "descricao": "Tranças box braids clássicas",
    "duracao_minutos": 180,
    "valor_total": "150.00",
    "valor_sinal": "50.00",
    "imagens": ["https://exemplo.com/img.jpg"],
    "ativo": true
  }')
echo "$TRANCA_RESPONSE" | jq .

TRANCA_ID=$(echo "$TRANCA_RESPONSE" | jq -r '.id')
echo "Trança criada com ID: $TRANCA_ID"
echo ""

# Criar cliente
echo "4. Criar Cliente..."
CLIENTE_RESPONSE=$(curl -s -X POST "$BASE_URL/clientes" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Maria Silva",
    "telefone": "11999999999",
    "email": "maria@email.com"
  }')
echo "$CLIENTE_RESPONSE" | jq .

CLIENTE_ID=$(echo "$CLIENTE_RESPONSE" | jq -r '.id')
echo "Cliente criado com ID: $CLIENTE_ID"
echo ""

# Consultar disponibilidade
echo "5. Consultar Disponibilidade..."
DATA_HORA=$(date -u -v+1d +"%Y-%m-%dT10:00:00" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT10:00:00" 2>/dev/null || echo "2024-12-25T10:00:00")
curl -s "$BASE_URL/agenda/disponibilidade?data=$DATA_HORA&tranca_id=$TRANCA_ID" | jq .
echo ""

# Criar agendamento
echo "6. Criar Agendamento..."
AGENDAMENTO_RESPONSE=$(curl -s -X POST "$BASE_URL/agenda/agendamentos" \
  -H "Content-Type: application/json" \
  -d "{
    \"cliente_id\": $CLIENTE_ID,
    \"tranca_id\": $TRANCA_ID,
    \"data_hora\": \"$DATA_HORA\",
    \"observacoes\": \"Teste de agendamento\"
  }")
echo "$AGENDAMENTO_RESPONSE" | jq .

AGENDAMENTO_ID=$(echo "$AGENDAMENTO_RESPONSE" | jq -r '.id')
echo "Agendamento criado com ID: $AGENDAMENTO_ID"
echo ""

# Confirmar pagamento
echo "7. Confirmar Pagamento do Sinal..."
curl -s -X POST "$BASE_URL/pagamentos/sinal" \
  -H "Content-Type: application/json" \
  -d "{
    \"agendamento_id\": $AGENDAMENTO_ID,
    \"valor\": 50.00
  }" | jq .
echo ""

# Resumo financeiro
echo "8. Resumo Financeiro..."
INICIO=$(date -u +"%Y-%m-01T00:00:00" 2>/dev/null || echo "2024-12-01T00:00:00")
FIM=$(date -u +"%Y-%m-%dT23:59:59" 2>/dev/null || echo "2024-12-31T23:59:59")
curl -s "$BASE_URL/financeiro/resumo?inicio=$INICIO&fim=$FIM" | jq .
echo ""

echo "✅ Testes concluídos!"

