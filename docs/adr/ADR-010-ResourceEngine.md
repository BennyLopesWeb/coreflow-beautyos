# ADR-010 — Resource Engine v1 (Meta Model Definitivo)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Estende** | [ADR-007](./ADR-007-ResourceEngine.md) |
| **Relacionado** | ADR-029, ADR-030 |

---

## Contexto

ADR-007 estabeleceu Resource Engine parcial. Ambiguidade persistia: profissional vs cadeira vs tranca. A Constituição proíbe terminologia vertical no core.

## Decisão — Meta Model Definitivo

### Três conceitos distintos (NUNCA confundir)

| Conceito | Definição | Reservável? | Executa serviço? |
|----------|-----------|-------------|------------------|
| **Resource** | Entidade física/lógica **ocupada** durante booking | ✅ Sim | ❌ Não |
| **Worker** | Pessoa/sistema que **executa** o serviço | ⚠️ Alocável (não reserva primária) | ✅ Sim |
| **Asset** | Ativo controlado (estoque, equipamento permanente) | ❌ Não (R2) | ❌ Não |

### Respostas explícitas (obrigatório)

| Entidade do mundo real | Classificação Core | Justificativa |
|------------------------|-------------------|---------------|
| **Cadeira** | ✅ **Resource** | Ocupada durante atendimento; capacity=1 |
| **Profissional** | ✅ **Worker** | Executa serviço; pode ser alocado a resource |
| **Quadra** | ✅ **Resource** | Espaço reservável; capacity configurável |
| **Consultório** | ✅ **Resource** | Sala/espaço reservável |
| **Equipamento** (secador, aparelho) | ✅ **Resource** (tipo `equipment`) OU **Asset** se não reservável individualmente | Reservável → Resource; pool compartilhado → Asset R3 |
| **Veículo** | ✅ **Resource** (tipo `vehicle`) | Unidade reservável (transporte, delivery) |
| **Sala** | ✅ **Resource** (tipo `room`) | Genérico |
| **Piscina** | ✅ **Resource** (tipo `pool`) | Facility com capacity |
| **Mesa** | ✅ **Resource** (tipo `table`) | Restaurante, coworking |

**Regra de ouro:** Se o cliente "reserva" o uso exclusivo ou slot de algo → **Resource**. Se alguém/algo **presta** o serviço → **Worker**.

### Tranca (legado) ≠ Resource direto

| Legado | Core R2 | Mapeamento |
|--------|---------|------------|
| `Tranca` (catálogo beauty) | **Catalog/Offering** | Tranca é agrupador comercial, NÃO resource |
| Cadeira física | **Resource** | ACL: `resource_id` ↔ legado seat/chair |
| Profissional | **Worker** | ACL: `worker_id` ↔ legado user/professional |

**Correção meta model:** `CoreMetaModel.md` mapeia Catalog→Tranca (comercial). Resource Engine **não** modela Tranca.

### Resource attributes (v1)

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `id` | UUID | ✅ |
| `company_id` | UUID | ✅ |
| `location_id` | UUID | ✅ |
| `resource_type` | string (plugin-defined) | ✅ |
| `name` | string | ✅ |
| `capacity` | int ≥1 | ✅ |
| `status` | active/inactive/maintenance | ✅ |
| `metadata` | JSON (plugin extension) | ❌ |

`resource_type` valores semânticos vêm do **plugin manifest** (`resource_types: [chair, court, room]`). Core **não** interpreta semântica.

### Worker attributes (v1 — read existing)

Worker alocado via `worker_id` em booking. Scheduling verifica **disponibilidade conjunta** Resource + Worker quando ambos required.

### Engine rules (imutáveis)

1. SchedulingEngine referencia apenas `resource_id`, `worker_id`, `capacity`, blocks
2. Zero strings `tranca`, `chair`, `court` em código engine
3. Conflitos via `ResourceConflictService` genérico
4. Plugin manifest declara `resource_types` + terminology labels

## Matriz de decisão — profissional como Resource?

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Profissional = Resource | ❌ Confunde executor com slot |
| B | Profissional = Worker; cadeira = Resource | ✅ Escolhida |
| C | Profissional = Resource tipo `worker` | ❌ Viola meta model |

## Consequências

- F3 implementa `modules/resource/` + `/v1/resources`
- Scheduling consome `ResourcePort` (F3)
- Beauty manifest: `resource_types: [chair]`, terminology `resource: Cadeira`

## Referências

- `docs/ResourceEngine.md`
- `docs/CoreMetaModel.md`
- ADR-001, ADR-007, ADR-008
