# CoreFlow — Engineering Handbook

**Documento:** `docs/EngineeringHandbook.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Normativo — complementa a Constituição  
**Audiência:** Todos os engenheiros CoreFlow e contribuidores de plugins

---

## 1. Arquitetura

### Estilo

**Modular Monolith** — único deployable com bounded contexts em `app/modules/`.

| Princípio | Implementação |
|-----------|---------------|
| API First | Regra de negócio na API FastAPI |
| Strangler Fig | Legado + v1 coexistem com ACL e flags |
| Plugin First | Vertical via manifest, não fork |
| No microservices by default | Extração só com métricas (ver `ArchitectureMetrics.md`) |

### Estrutura backend

```
backend/app/
├── core/           # Config, flags, enforcement, plugin loader, metamodel
├── modules/        # Bounded contexts (identity, booking, …)
├── shared/         # Events, ACL — Shared Kernel
├── routers/        # HTTP adapters (v1_*, legado)
├── services/       # LEGACY — não expandir
├── models/         # LEGACY ORM — sunset
├── plugins/        # Runtime plugin code (hooks, agents)
backend/plugins/    # Manifests YAML (beauty, clinic, sports)
```

### Camadas por módulo (alvo R2+)

```
modules/{context}/
├── domain/         # Entities, value objects, domain events
├── application/    # Services, commands, queries, ports (interfaces)
├── infrastructure/ # Repositories, adapters, ORM mappers
└── api/            # Routers FastAPI (opcional — ou routers/ central)
```

**Estado atual:** maioria dos módulos tem domain + application; infrastructure 🔜 R2.

---

## 2. DDD (Domain-Driven Design)

### Bounded contexts

Documentados em `docs/BoundedContexts.md`. Cada módulo = um contexto (ou subcontexto).

### Linguagem ubíqua

- Código core: **inglês** — `Booking`, `Offering`, `Worker`
- UI: **terminology do plugin** — "Reserva", "Modelo", "Profissional"
- Legado: **português** — não usar em código novo

### Aggregates

| Aggregate | Root | ID scope |
|-----------|------|----------|
| Booking | `CoreBooking` | per company |
| Catalog | `CoreCatalog` | per company |
| Customer | `CoreCustomer` | per company |

### Domain events

Preferir eventos a chamadas síncronas cross-context. Ver `EventCatalog.md`.

---

## 3. Hexagonal Architecture

### Ports & Adapters

```
[HTTP Router] → [Application Service] → [Port] ← [Adapter]
                                              ← [Legacy Service via ACL]
                                              ← [Repository / DB]
```

### Regras

| Camada | Pode | Não pode |
|--------|------|----------|
| **Domain** | Entidades, regras puras | SQLAlchemy, HTTP, Kafka |
| **Application** | Orquestração, ports | Import models legado |
| **Infrastructure** | ORM, Kafka, external APIs | Regra de negócio |
| **API/Router** | HTTP, validação, deps | Lógica de domínio |

### ACL obrigatória

Core ↔ Legado **sempre** via `shared/acl/`. Referência: `booking_port.py`.

---

## 4. Eventos

### Publicação

```python
event_bus.publish(db, DomainEvent(...))
# → handlers in-process
# → outbox row
# → kafka (se enabled)
# → ArchitectureMetricsStore (R1-F2)
```

### Convenções

- Nome: `{aggregate}.{action}`
- Payload: JSON-serializable, tenant-scoped
- Schema Avro para eventos externos
- Idempotência no consumer

### Outbox

Modos: `sync` | `deferred` | `rabbitmq` | `kafka` — config `OUTBOX_DISPATCH_MODE`.

DLQ: `KAFKA_DLQ_*` settings — replay worker em `workers/`.

---

## 5. API

### Versionamento

- Pública: `/v1/*` — semver API, breaking = `/v2`
- Legado: sem versionamento — sunset
- Headers: `X-CoreFlow-Layer`, `X-CoreFlow-Enforcement`, `Deprecation`

### OpenAPI

Auto-gerado FastAPI — manter response models Pydantic v2.

### Padrões REST

| Operação | Método | Status |
|----------|--------|--------|
| Create | POST | 201 |
| Read | GET | 200 |
| Update | PUT/PATCH | 200 |
| Delete | DELETE | 204 |
| List | GET | 200 + pagination |

### Autenticação

JWT Bearer — claims: `sub`, `email`, `company_id`, `role`.

### Multi-tenant

Todo query tenant-scoped filtra `company_id` — nunca confiar em client input alone.

---

## 6. Frontend

### Stack

- **Expo ~50** + React Native 0.73 + Expo Router
- TypeScript strict
- `@coreflow/sdk` para APIs v1

### Regras

- Novo código: SDK only para `/v1/*`
- Terminology via plugin config API
- Deep links via manifest
- Não hardcodar "Tranca", "Agendamento" — usar labels dinâmicos

### Estrutura

```
frontend/app/          # Routes (Expo Router)
frontend/src/          # Components, hooks, services
packages/coreflow-sdk/   # Shared client
```

---

## 7. Flutter

**Status:** Future / opcional.

Expo é stack primária (CF-15→25 investimento EAS). Flutter só se ADR justificar (ex.: parceiro enterprise).

Se adotado: consumir `@coreflow/sdk` via dart FFI ou OpenAPI generator — mesma API.

---

## 8. Testing

### Backend

```bash
cd backend && pytest -o addopts=
```

| Tipo | Local | Quando |
|------|-------|--------|
| Unit | `tests/test_core/`, módulo | Domain, services puros |
| Integration | `tests/` + fixtures | API, DB, outbox |
| Paridade | `tests/test_core/test_cf*.py` | Migração legado→v1 |

### Fixtures

`conftest.py`: `db`, `client`, `admin_headers`, `default_company`, entidades exemplo.

### Regras

- Comportamento novo = teste novo
- Paridade tests **antes** de enforcement block
- `PERSIST_DB=false` em testes (SQLite in-memory)
- Reset metrics: `ArchitectureMetricsStore.reset()` em testes R1-F2

### Frontend

Jest/Expo test — expandir Release 2+.

---

## 9. Logging

```python
from app.core.logging_config import get_logger
logger = get_logger("module_name")
logger.info("...", extra={"company_id": cid, "booking_id": bid})
```

| Nível | Uso |
|-------|-----|
| DEBUG | ACL delegation, event dispatch |
| INFO | Business milestones |
| WARNING | Enforcement warn, deprecated API use |
| ERROR | Exceptions, DLQ |

**Nunca** logar senhas, tokens, PII completa.

---

## 10. Observabilidade

| Ferramenta | Uso |
|------------|-----|
| Prometheus | HTTP metrics, custom counters |
| Grafana | Dashboards as code — `infra/grafana/` |
| Alertmanager | Rules as code — DLQ, API errors |
| OpenTelemetry | Tracing opcional — `setup_telemetry()` |
| Platform Health | `/v1/platform/health` |

Ver `docs/ArchitectureMetrics.md` para KPIs arquiteturais.

---

## 11. Git

### Branching

```
main          # Produção
feature/*     # Features
fix/*         # Bugfixes
release/*     # Release branches (opcional)
```

### PRs

- Uma fase por PR (Constituição)
- PR Checklist obrigatório
- Review arquitetural para mudanças cross-context

---

## 12. Commits

### Formato (Conventional Commits)

```
tipo(escopo): descrição curta

Corpo opcional — por quê, não o quê.
```

| Tipo | Uso |
|------|-----|
| `feat` | Nova capacidade |
| `fix` | Bugfix |
| `docs` | Documentação |
| `refactor` | Sem mudança comportamento |
| `test` | Testes |
| `chore` | Build, deps |

Exemplos:

```
feat(booking): add core create path behind feature flag
docs(platform): add PlatformVision strategic doc
fix(acl): track invocation metrics on resolve_legacy_ids
```

---

## 13. Versionamento

### APP_VERSION

Semver + sprint tag: `1.17.0-r1-f2`, `2.0.0-beta.1`

### API

Breaking change → `/v2` + período deprecação `/v1` + ADR.

### Eventos Avro

Backward compatible: add optional fields. Breaking → new major `.v2.avsc`.

### Plugins

Manifest `version` independente — `min_platform_version` no sdk block.

---

## 14. Feature Flags

### Mapa

| Flag | Setting | Default R1-F2 |
|------|---------|---------------|
| `booking.core.enabled` | `FEATURE_BOOKING_CORE_ENABLED` | false |
| `ai.core.enabled` | `FEATURE_AI_CORE_ENABLED` | false |
| `workflow.enabled` | `FEATURE_WORKFLOW_ENABLED` | false |
| `plugin.engine.enabled` | `FEATURE_PLUGIN_ENGINE_ENABLED` | false |
| `legacy.telemetry.enabled` | `FEATURE_LEGACY_TELEMETRY_ENABLED` | false |

### Regras

- Toda migração comportamental protegida por flag
- Default seguro (false) salvo exceção ADR
- Documentar rollback no sprint doc
- Expor via `GET /v1/platform/feature-flags`

---

## 15. ACL

### Quando usar

- Core → Legado (Strangler)
- Core → Sistema externo
- Plugin → Core (via API/ports, não ORM cross-module)

### Padrão

1. Definir `Protocol` em `shared/acl/{context}_port.py`
2. Implementar adapter em infrastructure
3. Registrar telemetria ACL
4. Feature flag para path novo
5. Testes com mock do legado

---

## 16. Documentação

### Hierarquia

| Tipo | Path | Quando atualizar |
|------|------|------------------|
| Constituição | `CONSTITUTION.md` | Raramente — ADR |
| Estratégico | `PlatformVision.md`, etc. | Por release |
| ADR | `docs/adr/` | Decisão arquitetural |
| RFC | `docs/rfc/` | Proposta |
| Sprint | `docs/sprints/` | Cada sprint |
| Vivos | Assessment, MetaModel, Roadmap | Cada sprint (DoD) |

### DoD Arquitetural

10 critérios em `docs/decisions/DefinitionOfDone-Architecture.md` — obrigatório antes de fechar sprint.

---

## Referências

- `docs/CONSTITUTION.md`
- `docs/DeveloperPortal.md`
- `docs/decisions/PR-Checklist.md`
- `docs/decisions/DefinitionOfDone-Architecture.md`
- `DOCUMENTACAO.md`
