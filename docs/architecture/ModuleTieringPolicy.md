# Module Tiering Policy — Classificação Oficial

**Versão:** 1.1  
**Data:** 2026-07-16  
**Autoridade:** Architecture Census (Phase 0) + Migration Matrix (Phase 1)  
**Regra:** Durante a migração, **nenhum módulo pode ser reclassificado** sem ADR ou emenda ao Decision Log.

**Emenda 2026-07-16 (R2-F3b):** `catalog` e `customer` reclassificados de CRUD → **CORE-SUPPORT** (hexagonal lite) para cumprir ADR-030 / FF-HEX-006. Flatten Wave 2 de catalog **cancelado**. Freeze flat de customer excepcionado para ports/repos/ACL.

---

## Tipos arquiteturais

| Tipo | Código | Arquitetura alvo | Pode flatten? |
|------|--------|------------------|:-------------:|
| **Core Domain** | `CORE` | Hexagonal completo — Aggregate, Domain Service, Ports, Adapters, Events, Outbox | ❌ Nunca |
| **Core Supporting** | `CORE-SUPPORT` | Hexagonal leve — Engine, event consumer, ports onde há valor | ❌ Nunca |
| **Support CRUD** | `CRUD` | Flat — `models.py`, `{module}_service.py`, `legacy_sync.py` (opcional) | ✅ Sim |
| **Support Operations** | `OPS` | Application services thin — sem ports/events | ⚠️ Reorganizar apenas |
| **Infrastructure** | `INFRA` | Shared kernel — Outbox, ACL, Idempotency, Feature Flags | ❌ Nunca |
| **Legacy (sunset)** | `LEGACY` | `app/services/`, `app/models/` — eliminar, não flatten | ❌ Sunset only |

---

## Classificação por módulo (fonte única)

### CORE — Hexagonal completo / leve — **KEEP**

| Módulo | Tipo | Notas |
|--------|------|-------|
| `booking` | **CORE** | Referência arquitetural do repositório |
| `scheduling` | **CORE** | Engine + ResourcePort; ORM OK para metamodelo |
| `payments` (write path) | **CORE** | Read = CRUD; write = hexagonal (R3) |
| `identity` | **CORE-SUPPORT** | Ports auth/repo; sem aggregate |
| `workflow` | **CORE-SUPPORT** | Event-driven engine |
| `push` | **CORE-SUPPORT** | Event consumer + Expo |
| `catalog` | **CORE-SUPPORT** | Hexagonal lite (R2-F3b) — Repository + QueryPort + ACL; sem aggregate |
| `customer` | **CORE-SUPPORT** | Hexagonal lite (R2-F3b) — Repository + QueryPort + ACL; service flat permanece facade |

### CRUD — Flat Architecture — **MIGRATE**

| Módulo | Tipo | Wave | Status |
|--------|------|------|--------|
| `inventory` | **CRUD** | 1 | ✅ DONE |
| `asset` | **CRUD** | 1 | TODO (P3) |
| `invoice` | **CRUD** | 1 | TODO (P4) |
| `order` | **CRUD** | 1 | TODO (P5) |
| `waitlist` | **CRUD** | 2 | TODO (P7) |
| `payments` (read) | **CRUD** | 2 | TODO (P8) — **sensitive** |

### OPS — Support Operations — **Wave 3**

| Módulo | Tipo | Notas |
|--------|------|-------|
| `platform` | **OPS** | Health, flags API |
| `observability` | **OPS** | Grafana/Alertmanager export |
| `mobile` | **OPS** | DevOps (EAS, Terraform, CDN) |
| `ai` | **OPS** | Provider pattern; BeautyAgent → plugin F4 |
| `marketplace` | **OPS** | Stub |

### INFRA — Nunca modificar na migração CRUD

| Componente | Tipo |
|------------|------|
| `shared/events/` (Outbox, Bus, Kafka, RabbitMQ) | **INFRA** |
| `shared/acl/` | **INFRA** |
| `shared/idempotency/` | **INFRA** |
| `shared/kernel/` | **INFRA** |
| `app/core/feature_flags.py` | **INFRA** |
| `app/core/core_enforcement.py` | **INFRA** |
| `app/workers/outbox_worker.py` | **INFRA** |

### LEGACY — Sunset (fora do escopo flatten)

| Camada | Tipo |
|--------|------|
| `app/services/` (20 arquivos) | **LEGACY** |
| `app/models/` (17 ORM legado) | **LEGACY** |
| Routers PT-BR legado | **LEGACY** |

---

## Critérios de flatten (12 condições — TODAS obrigatórias)

Um módulo só pode ser flatten quando **todas** forem verdadeiras:

1. ✓ Sem Aggregate Root  
2. ✓ Sem Domain Events  
3. ✓ Sem Event Publisher  
4. ✓ Sem Event Consumer  
5. ✓ Sem participação em Saga  
6. ✓ Sem integração Outbox  
7. ✓ Sem Middleware-Out  
8. ✓ Sem ACL  
9. ✓ Sem Feature Flags  
10. ✓ Sem Optimistic Lock  
11. ✓ Sem orquestração transacional  
12. ✓ Lógica CRUD apenas  

Se **qualquer** item for falso → **ABORT** — não simplificar.

---

## Critério de encerramento da migração

A migração Support CRUD está **completa** quando:

- [ ] Todos os módulos `CRUD` estão flat  
- [ ] Zero fake Ports em módulos CRUD  
- [ ] Zero fake Adapters em módulos CRUD  
- [ ] `booking` inalterado (hexagonal referência)  
- [ ] `scheduling` inalterado  
- [ ] `payments` write path inalterado até R3  
- [ ] Middleware-Out inalterado  
- [ ] Outbox inalterado  
- [ ] ACL inalterado  
- [ ] Feature Flags inalteradas  
- [ ] Migration Ledger atualizado  
- [ ] CI green (suite completa)
