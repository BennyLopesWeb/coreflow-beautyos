# Migration Ledger — Support CRUD Simplification

**Versão processo:** v3  
**Última atualização:** 2026-07-10  
**Fonte única de verdade** da migração arquitetural Support → Flat.

Classificação oficial: [ModuleTieringPolicy.md](./ModuleTieringPolicy.md)

---

## Ledger

| Module | Tier | Wave | Priority | Status | Commit | Architecture |
|--------|------|------|----------|--------|--------|--------------|
| `inventory` | CRUD | 1 | P1 | **DONE** | `7b3328a` | Flat |
| `customer` | CRUD | 1 | P2 | **DONE** | `0cad7dc` | Flat |
| `asset` | CRUD | 1 | P3 | TODO | — | CRUD Flat (target) |
| `invoice` | CRUD | 1 | P4 | TODO | — | CRUD Flat (target) |
| `order` | CRUD | 1 | P5 | TODO | — | CRUD Flat (target) |
| `catalog` | CRUD | 2 | P6 | TODO | — | CRUD Flat (target) — **sensitive** |
| `waitlist` | CRUD | 2 | P7 | TODO | — | CRUD Flat (target) |
| `payments` (read) | CRUD | 2 | P8 | TODO | — | CRUD Flat (target) — **sensitive** |
| `platform` | OPS | 3 | P9 | TODO | — | OPS thin |
| `observability` | OPS | 3 | P10 | TODO | — | OPS thin |
| `ai` | OPS | 3 | P12 | TODO | — | OPS thin |
| `mobile` | OPS | 3 | P13 | TODO | — | OPS subpackages |
| `marketplace` | OPS | 3 | P11 | SKIP | — | Já minimal |
| `booking` | CORE | — | — | **KEEP** | — | Hexagonal |
| `scheduling` | CORE | — | — | **KEEP** | — | Hexagonal |
| `payments` (write) | CORE | — | — | **KEEP** | — | Hexagonal (R3) |
| `identity` | CORE-SUPPORT | — | — | **KEEP** | — | Hexagonal lite |
| `workflow` | CORE-SUPPORT | — | — | **KEEP** | — | Event engine |
| `push` | CORE-SUPPORT | — | — | **KEEP** | — | Event consumer |

---

## Processo v3 — Execução por módulo

### STEP 0 — Dependency Scan (obrigatório, **antes** do refactor)

```bash
./scripts/migration/dependency_scan.sh <module>
```

Produz:

- **Inbound imports** — quem importa o módulo  
- **Outbound imports** — o que o módulo importa  
- **Public symbols** — classes/funções expostas  
- **Coupling metrics** — inbound/outbound count, import depth, package depth  

**Gate:** grafo revisado e aprovado (`APPROVED Pn`) antes de editar código.

### STEP 1 — Classificação

Confirmar tier em [ModuleTieringPolicy.md](./ModuleTieringPolicy.md).  
Se `CORE` ou `CORE-SUPPORT` → **ABORT**.

### STEP 2 — Flatten (1 módulo, ≤15 arquivos, ≤800 LOC)

Estrutura alvo CRUD:

```
modules/{module}/
├── models.py
├── {module}_service.py
└── legacy_sync.py   # se existir sync legado
```

Após remover `.py` de `domain/` e `application/`, **remover pastas vazias** (e `__pycache__` residual).

**Imports cruzados:** apenas atualização de path — zero alteração de lógica fora do módulo.

**Aliases:** proibidos se 0 consumers; se temporários → `TODO(Migration R2)` + data remoção.

### STEP 3 — Architecture Lint (automático)

```bash
./scripts/migration/architecture_lint.sh <module>
```

Falha em paths proibidos no módulo migrado → **ABORT**.

### STEP 4 — Dependency Gate

```bash
python -m compileall -q backend/app/modules/<module>
python -m pip check
pytest tests/ -q -o addopts=
```

### STEP 5 — Definition of Done (arquitetural)

Módulo considerado migrado **somente se**:

- [ ] Sem fake `domain/` layer  
- [ ] Sem fake `application/` layer  
- [ ] Sem Ports vazios  
- [ ] Sem Adapters vazios  
- [ ] Sem Service envolvendo Service sem valor  
- [ ] Sem Repository envolvendo Repository sem valor  
- [ ] Sem interfaces mortas  
- [ ] Sem aliases órfãos  
- [ ] Public REST API inalterada  
- [ ] Schema DB inalterado  
- [ ] Architecture Integrity checklist ✓  
- [ ] Tests green  

### STEP 6 — Pre-Commit Gate

| Check | Obrigatório |
|-------|:-----------:|
| Tests PASS | ✓ |
| REST smoke PASS | ✓ |
| DB unchanged | ✓ |
| Events unchanged | ✓ |
| Feature Flags unchanged | ✓ |
| Outbox unchanged | ✓ |
| Middleware-Out unchanged | ✓ |
| No Core modules modified | ✓ |
| Only approved module changed* | ✓ |
| Architecture Lint PASS | ✓ |
| Prohibited path grep 0 matches | ✓ |

\* Imports-only em outros módulos permitidos (policy §cross-import).

### STEP 7 — Commit + Ledger + Architecture Freeze

1. Commit: `refactor(<module>): simplify architecture`  
2. Atualizar este Ledger (Status, Commit)  
3. Preencher **Architecture Debt Report** (seção abaixo)  
4. **Architecture Freeze** no módulo — ver abaixo  

---

## Architecture Freeze (pós-commit)

Após marcar **DONE** no Ledger, o módulo entra em freeze:

| Permitido | Proibido |
|-----------|----------|
| bug fix | novo refactor estrutural |
| test fix | reabrir pastas domain/application |
| import path fix (compat) | adicionar ports/adapters |
| | alterar contrato REST |

---

## Módulos sensíveis — gate extra (P6, P8)

Antes do commit em `catalog` ou `payments` (read):

### Dependency Contract Verification

- [ ] Public imports documentados no STEP 0  
- [ ] Public classes listadas  
- [ ] `booking` adapters que consomem o módulo identificados  
- [ ] Legacy sync behavior unchanged  
- [ ] Smoke test Booking (create / approve se payments)  
- [ ] CF tests do módulo + paridade  

---

## Architecture Debt Report (template pós-commit)

```markdown
### Architecture Debt — {module} ({commit})

**Removed:**
- [ ] application/ layer
- [ ] domain/ layer
- [ ] fake ports
- [ ] fake adapters
- [ ] dead interfaces

**Remaining (expected for CRUD):**
- legacy_sync (until P0 runner)
- service
- router (external)
- models (ORM)

**Coupling:**
| Metric | Before | After | Δ |
|--------|--------|-------|---|
| Inbound deps | | | |
| Outbound deps | | | |
| Import depth | | | |
| Package depth | | | |

**Estimated debt reduction:** ___%
```

---

## P1 + P2 — Registro histórico

### inventory (`7b3328a`)

| Métrica | Before | After |
|---------|--------|-------|
| Inbound | 6 (asset, router, alembic, init_db, conftest, cf10) | 6 |
| Outbound | 2 (db.base, exceptions) | 2 |
| Package depth | 3 (`inventory.domain.models`) | 2 (`inventory.models`) |
| Architecture Score | — | ~43% reduction |

### customer (`0cad7dc`)

| Métrica | Before | After |
|---------|--------|-------|
| Inbound | 7 (+ waitlist) | 7 |
| Outbound | 3 (cliente ORM, logging, models) | 3 |
| Package depth | 3 | 2 |
| Architecture Score | — | ~43% reduction |

---

## P3 asset — STEP 0 (pré-aprovado, não executado)

**Inbound (9 arquivos):**

| Consumer | Symbol |
|----------|--------|
| `routers/v1_assets.py` | `AssetQueryService`, `AssetLegacySyncService` |
| `routers/v1_inventory.py` | `AssetLegacySyncService` |
| `db/init_db.py` | `CoreAsset`, `AssetLegacySyncService` |
| `alembic/env.py` | `CoreAsset` |
| `tests/conftest.py` | `CoreAsset` |
| `tests/test_cf10_*.py` | `CoreAsset`, `AssetLegacySyncService` |
| `modules/inventory` (indirect) | sync via inventory router only |

**Outbound:**

| Target | Purpose |
|--------|---------|
| `app.models.inventory_item` | Legacy sync source |
| `app.modules.inventory.models` | Creates `CoreInventory` on sync |
| `app.core.logging_config` | Logger |

**Public symbols:** `CoreAsset`, `AssetQueryService`, `AssetLegacySyncService`

**Coupling:** inbound 9, outbound 3, package depth 3 → target 2

**Aguardando:** `APPROVED P3`

---

## Comparação P1 vs P2 — padrão validado

| Critério | P1 | P2 |
|----------|:--:|:--:|
| Architecture Score ~43% | ✅ | ✅ |
| 0 prohibited paths | ✅ | ✅ |
| 318 tests PASS | ✅ | ✅ |
| 0 aliases | ✅ | ✅ |
| Core untouched | ✅ | ✅ |

**Padrão aprovado para P3+.**
