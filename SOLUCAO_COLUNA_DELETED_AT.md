# ✅ Solução: Erro "no such column: clientes.deleted_at"

## 🔍 Problema Identificado

Ao tentar criar um cliente, você recebia este erro:

```
sqlite3.OperationalError: no such column: clientes.deleted_at
```

**Causa**: O banco de dados foi criado antes de adicionarmos a coluna `deleted_at` para soft delete nos models. O SQLAlchemy não atualiza automaticamente tabelas existentes quando você modifica os models.

## ✅ Solução Aplicada

Foi criado e executado um script de migração que adiciona a coluna `deleted_at` em todas as tabelas necessárias:

- ✅ `clientes` - Adicionada
- ✅ `trancas` - Adicionada
- ✅ `agendamentos` - Adicionada
- ✅ `fila` - Adicionada
- ✅ `financeiro` - Adicionada
- ✅ `users` - Já existia

## 📝 Script de Migração

O script `backend/app/db/migrate_add_deleted_at.py` foi criado para:

1. Verificar quais tabelas existem
2. Verificar se a coluna `deleted_at` já existe
3. Adicionar a coluna se não existir
4. Executar de forma segura (com rollback em caso de erro)

## 🚀 Como Usar

### Executar Migração Manualmente

Se precisar executar a migração novamente:

```bash
cd backend
python3 -m app.db.migrate_add_deleted_at
```

### Verificar Estrutura da Tabela

```bash
cd backend
sqlite3 trancapro.db ".schema clientes"
```

## ✅ Teste de Validação

Agora você pode criar clientes normalmente:

```bash
# 1. Fazer login e obter token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"benny4@gmail.com","password":"senha123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Criar cliente
curl -X POST "http://localhost:8000/clientes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "nome": "Francoise",
    "telefone": "4738092830982",
    "email": "fran@email.com"
  }'
```

## 📋 Estrutura da Tabela Agora

A tabela `clientes` agora tem:

```sql
CREATE TABLE clientes (
    id INTEGER NOT NULL,
    nome VARCHAR NOT NULL,
    telefone VARCHAR NOT NULL,
    email VARCHAR,
    deleted_at DATETIME,  -- ✅ NOVA COLUNA
    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
    updated_at DATETIME,
    PRIMARY KEY (id)
);
```

## ⚠️ Nota Importante

- A coluna `deleted_at` permite **soft delete** (exclusão lógica)
- Quando um registro é "deletado", apenas o campo `deleted_at` é preenchido
- Registros com `deleted_at IS NULL` são considerados ativos
- Isso permite recuperar dados "deletados" se necessário

## 🎯 Status

- ✅ Migração executada com sucesso
- ✅ Todas as tabelas atualizadas
- ✅ Endpoint de criação de clientes funcionando
- ✅ Soft delete implementado

---

**Data da correção**: 27/12/2025
**Status**: ✅ Resolvido e testado

