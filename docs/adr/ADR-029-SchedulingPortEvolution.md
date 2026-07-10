# ADR-029 — Scheduling Port Evolution

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-010, ADR-025 |

---

## Contexto

Scheduling ainda resolve `legacy_tranca_id` e `tranca_id` em availability. Booking core path (F1) precisa de abstração antes Resource Engine (F3).

## Decisão — Evolução em 4 estágios (sem quebra)

### Estágio 0 (hoje — pré R2)

```
Booking Command → ReservationService → LegacySchedulingAdapter → tranca_id
```

### Estágio 1 (R2-F0.5 / F1) — SchedulingPort interim

```
Booking Application → SchedulingPort → LegacySchedulingAdapter (ACL)
                                              ↓
                                    maps resource_id ↔ tranca internally
```

**SchedulingPort interface (v1):**

| Método | Parâmetros |
|--------|------------|
| `check_availability` | `company_id`, `resource_id`, `worker_id?`, `starts_at`, `ends_at` |
| `reserve_slot` | same (optional hold) |
| `release_slot` | `booking_id` |

Adapter ACL traduz `resource_id` → legado internamente até F3.

### Estágio 2 (R2-F3) — ResourcePort

```
Scheduling Application → ResourcePort → CoreResourceRepository
SchedulingEngine → resource_id (no tranca)
LegacySchedulingAdapter DEPRECATED (flag OFF path only)
```

**ResourcePort:**

| Método | Descrição |
|--------|-----------|
| `get_resource(resource_id)` | Core resource |
| `list_by_location(location_id)` | CRUD support |

SchedulingEngine consumes ResourcePort; zero `legacy_tranca_id` in new code (FF-SCH-001).

### Estágio 3 (R3) — Scheduling Engine v2

- Multi-resource booking
- Parent/child resources
- Separate ADR-008 v2

### Compatibilidade

| Flag combo | Behavior |
|------------|----------|
| BOOKING ON, RESOURCE OFF | SchedulingPort + ACL tranca mapping |
| BOOKING ON, RESOURCE ON | ResourcePort + core_resources |
| BOOKING OFF | Legado unchanged |

### Proibido em código novo (F1+)

- Variable names `tranca_id`, `legacy_tranca_id` outside ACL adapters
- Import `app.models.tranca` outside ACL

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Wait F3 for any booking core | ❌ Blocks F1 |
| B | SchedulingPort interim → ResourcePort | ✅ Escolhida |
| C | Keep tranca in booking commands | ❌ Violates meta model |

## Consequências

- F1 requires SchedulingPort (even if ACL-backed)
- F3 removes tranca from scheduling engine new path
- ADR-008 v2 deferred R3

## Referências

- ADR-008 Scheduling Engine
- ADR-010 Resource Engine
- `docs/ResourceEngine.md`
