# 📋 Plano de Implementação - Backend MVP

## 🎯 Objetivo
Implementar backend completo em FastAPI para sistema de agendamento e CRM de trancista, pronto para consumo por React Web, React Native e WhatsApp.

---

## 📊 Análise de Requisitos

### ✅ O que temos:
- Documentação completa do sistema anterior
- Estrutura de diretórios definida
- Stack tecnológica definida

### ❌ O que falta:
1. **Estrutura de diretórios** conforme especificação
2. **Models** (SQLAlchemy) para todas as entidades
3. **Schemas** (Pydantic) para validação
4. **Routers** com todos os endpoints obrigatórios
5. **Services** com regras de negócio
6. **Configuração do banco** (SQLite para MVP)
7. **Core** (config, database, exceptions)

---

## 🏗️ Estrutura de Entidades

### 1. Cliente
```python
- id: int
- nome: str
- telefone: str (único)
- email: str (opcional)
- created_at: datetime
- updated_at: datetime
```

### 2. Tranca
```python
- id: int
- nome: str
- descricao: str (opcional)
- duracao_minutos: int
- valor_total: decimal
- valor_sinal: decimal
- imagens: list[str] (URLs)
- ativo: bool
- created_at: datetime
- updated_at: datetime
```

### 3. Agendamento
```python
- id: int
- cliente_id: int (FK)
- tranca_id: int (FK)
- data_hora: datetime
- sinal_pago: bool (default: False)
- status: enum (pendente, confirmado, cancelado, concluido)
- observacoes: str (opcional)
- created_at: datetime
- updated_at: datetime
```

### 4. Fila
```python
- id: int
- agendamento_id: int (FK, único)
- data: date
- posicao: int
- created_at: datetime
```

### 5. Financeiro
```python
- id: int
- tipo: enum (entrada, saida)
- descricao: str
- valor: decimal
- agendamento_id: int (FK, opcional)
- data: datetime
- created_at: datetime
```

---

## 🔌 Endpoints Obrigatórios

### Catálogo de Tranças
- `GET /trancas` - Lista todas as tranças ativas
- `POST /trancas` - Cria nova trança (admin)

### Agendamento
- `GET /agenda/disponibilidade?data={date}&tranca_id={id}` - Horários disponíveis
- `POST /agendamentos` - Cria novo agendamento

### Pagamento
- `POST /pagamentos/sinal` - Confirma pagamento do sinal (mock)

### Fila Virtual
- `POST /fila/entrar` - Entra na fila
- `GET /fila/{data}` - Consulta fila do dia

### Financeiro
- `GET /financeiro/resumo?inicio={date}&fim={date}` - Resumo financeiro
- `POST /financeiro/saida` - Registra saída manual

### WhatsApp (Mock)
- `POST /webhook/whatsapp` - Recebe mensagens do WhatsApp

---

## 🧠 Regras de Negócio

### 1. Horários Disponíveis
- ✅ Verifica conflitos com agendamentos existentes
- ✅ Considera duração da trança
- ✅ Não permite agendamentos no passado
- ✅ Bloqueia horários se fila estiver ativa para o dia

### 2. Agendamento
- ✅ Só confirma se `sinal_pago = true`
- ✅ Cria entrada financeira automática ao confirmar sinal
- ✅ Status inicial: `pendente`
- ✅ Ao confirmar: `confirmado` + cria entrada financeira

### 3. Fila Virtual
- ✅ Ativa quando dia está lotado
- ✅ Bloqueia novos agendamentos para o dia
- ✅ Posição calculada automaticamente
- ✅ Uma fila por dia

### 4. Financeiro
- ✅ Toda entrada deve ser registrada
- ✅ Entradas automáticas ao confirmar sinal
- ✅ Saídas manuais
- ✅ Resumo calcula: total_entradas, total_saidas, saldo

### 5. Validações
- ✅ Telefone único por cliente
- ✅ Valor sinal <= valor total
- ✅ Duração > 0
- ✅ Data/hora não pode ser no passado

---

## 💡 Sugestões de Melhorias

### 1. Estrutura
- ✅ Separar routers por domínio (trancas, agendamentos, etc)
- ✅ Services com lógica de negócio isolada
- ✅ Repositories para abstração de dados (opcional para MVP)

### 2. Segurança
- ⚠️ Adicionar autenticação JWT (não obrigatório no MVP, mas preparar estrutura)
- ⚠️ Rate limiting para endpoints públicos
- ⚠️ Validação de entrada rigorosa

### 3. Performance
- ⚠️ Cache para consultas de disponibilidade (futuro)
- ⚠️ Índices no banco de dados
- ⚠️ Paginação em listagens

### 4. Observabilidade
- ⚠️ Logging estruturado
- ⚠️ Health check endpoint
- ⚠️ Métricas básicas

### 5. Testes
- ⚠️ Testes unitários dos services
- ⚠️ Testes de integração dos endpoints
- ⚠️ Fixtures para dados de teste

### 6. Documentação
- ✅ OpenAPI/Swagger automático (FastAPI)
- ⚠️ README com exemplos de uso
- ⚠️ Comentários no código

---

## 📁 Estrutura de Arquivos Proposta

```
backend/
└─ app/
   ├─ main.py                 # Aplicação FastAPI
   ├─ models/
   │  ├─ __init__.py
   │  ├─ cliente.py
   │  ├─ tranca.py
   │  ├─ agendamento.py
   │  ├─ fila.py
   │  └─ financeiro.py
   ├─ schemas/
   │  ├─ __init__.py
   │  ├─ cliente.py
   │  ├─ tranca.py
   │  ├─ agendamento.py
   │  ├─ fila.py
   │  └─ financeiro.py
   ├─ routers/
   │  ├─ __init__.py
   │  ├─ trancas.py
   │  ├─ agendamentos.py
   │  ├─ pagamentos.py
   │  ├─ fila.py
   │  ├─ financeiro.py
   │  └─ webhook.py
   ├─ services/
   │  ├─ __init__.py
   │  ├─ tranca_service.py
   │  ├─ agendamento_service.py
   │  ├─ disponibilidade_service.py
   │  ├─ fila_service.py
   │  └─ financeiro_service.py
   ├─ db/
   │  ├─ __init__.py
   │  ├─ base.py
   │  ├─ session.py
   │  └─ init_db.py
   └─ core/
      ├─ __init__.py
      ├─ config.py
      ├─ exceptions.py
      └─ dependencies.py
```

---

## 🚀 Ordem de Implementação

1. ✅ **Core** - Config, database, exceptions
2. ✅ **Models** - Todas as entidades SQLAlchemy
3. ✅ **Schemas** - Todos os Pydantic schemas
4. ✅ **Services** - Lógica de negócio
5. ✅ **Routers** - Endpoints da API
6. ✅ **Main** - Aplicação FastAPI
7. ✅ **Init DB** - Script de inicialização

---

## 📝 Checklist de Implementação

### Core
- [ ] config.py - Configurações da aplicação
- [ ] database.py - Setup SQLAlchemy
- [ ] exceptions.py - Exceções customizadas
- [ ] dependencies.py - Dependências FastAPI

### Models
- [ ] Cliente
- [ ] Tranca
- [ ] Agendamento
- [ ] Fila
- [ ] Financeiro

### Schemas
- [ ] Cliente (Create, Read, Update)
- [ ] Tranca (Create, Read, Update)
- [ ] Agendamento (Create, Read, Update)
- [ ] Fila (Create, Read)
- [ ] Financeiro (Create, Read)
- [ ] Disponibilidade (Response)
- [ ] Resumo Financeiro (Response)

### Services
- [ ] TrancaService
- [ ] DisponibilidadeService
- [ ] AgendamentoService
- [ ] FilaService
- [ ] FinanceiroService

### Routers
- [ ] GET /trancas
- [ ] POST /trancas
- [ ] GET /agenda/disponibilidade
- [ ] POST /agendamentos
- [ ] POST /pagamentos/sinal
- [ ] POST /fila/entrar
- [ ] GET /fila/{data}
- [ ] GET /financeiro/resumo
- [ ] POST /financeiro/saida
- [ ] POST /webhook/whatsapp

### Main
- [ ] FastAPI app
- [ ] CORS config
- [ ] Router registration
- [ ] Health check

---

## 🎯 Resultado Esperado

- ✅ API funcional e testável
- ✅ Regras de negócio centralizadas nos services
- ✅ Base sólida para frontend e mobile
- ✅ Código limpo e comentado
- ✅ Pronto para evoluir (autenticação, cache, etc)

---

**Próximo passo**: Implementar seguindo este plano

