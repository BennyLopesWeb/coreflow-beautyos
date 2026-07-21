# ADR-032 — Feature Flag Lifecycle (R2)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-024, RFC-003 |

---

## Contexto

R2 introduz 4+ flags. Flag debt sem lifecycle gera complexidade permanente.

## Decisão — Registro obrigatório por flag

Cada flag R2 **deve** ter entrada nesta tabela (atualizar em sprint docs):

| Flag | Owner | Criada | Objetivo | Critério remoção | Remoção prevista | Aprovador remoção |
|------|-------|--------|----------|------------------|------------------|-------------------|
| `FEATURE_BOOKING_CORE_ENABLED` | Platform Lead | R2-F1 | Strangler booking domain | 100% tenants ON 30d + legado block | R3-F2 | ARB |
| `FEATURE_RESOURCE_ENGINE_ENABLED` | Platform Lead | R2-F3 | Resource Engine v1 | Scheduling sem tranca_id | R3-F3 | ARB |
| `FEATURE_PLUGIN_ENGINE_ENABLED` | Platform Lead | R2-F4 | Typed plugin dispatch | BeautyAgent migrated + tests | R3-F4 | ARB |
| `EXPO_PUBLIC_USE_SDK_BOOKINGS` | Frontend Lead | R3 | SDK admin tab | Tab legado removed | R3-F5 | Product + ARB |
| `CORE_ENFORCEMENT_MODE` | Platform Lead | R1 | warn/block legado | All routes migrated or 410 | R4 | ARB |
| `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` | Platform Lead | R4-F2 | Kill-switch dual-write outbound (`project_*`, ADR-024 sunset) | Zero uso da flag em produção por período de observação | R4-F3 | ARB |

### Lifecycle phases

```
created → dev_testing → staging_canary → prod_canary → prod_full → sunset_scheduled → removed
```

### Rules

| Rule | Detail |
|------|--------|
| Default | Always `false` / `warn` for new flags |
| Removal PR | Must remove flag + dead code path in same PR |
| Max age | Flag >2 releases past removal date → P1 debt |
| Documentation | Sprint doc references flag + rollback |
| Telemetry | Metric per flag state required F5 |

### Rollback (per flag)

Documented in each sprint doc — env var flip <5 min.

### Flag debt prevention

- Quarterly ARB review of active flags
- `docs/sprints/R2-F*.md` must include flag section
- FF-FLAG-001 validates sprint doc mentions flag

## Consequências

- No new flag without ADR-032 table update
- R3 begins flag removal wave

## Referências

- `docs/FeatureFlagPlatform.md`
- RFC-003 §6
