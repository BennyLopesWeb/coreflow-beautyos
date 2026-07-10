# ADR-033 — Enforcement Block Scope

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-024, RFC-002 |

---

## Contexto

RFC-002 define enforcement gradual. R2-F6 ativa block — escopo incorreto quebra payments, fila, waitlist legado.

## Decisão

### Escopo NARROW (R2-F6)

**Block applies ONLY to routes with 100% paridade + flag ON validated:**

| Rota legado (write) | v1 equivalente | Block R2-F6? |
|---------------------|----------------|--------------|
| `POST /agendamentos` | `POST /v1/bookings` | ✅ staging |
| `PUT /agendamentos/{id}` (approve) | `POST /v1/bookings/{id}/approve` | ✅ staging |
| `PUT /agendamentos/{id}` (reject) | `POST /v1/bookings/{id}/reject` | ✅ staging |
| `DELETE /agendamentos/{id}` (cancel) | `POST /v1/bookings/{id}/cancel` | ✅ staging |
| `POST /payments/*` | `POST /v1/payments` | ❌ R3 |
| `POST /fila/*` | `POST /v1/waitlist` | ❌ R3 |
| `POST /trancas/*` | `POST /v1/catalogs` | ❌ R3 |
| `GET /*` (reads) | — | ❌ Never block R2 |

### Modos

| Mode | Writes legado booking | Behavior |
|------|----------------------|----------|
| `off` | Allowed | No middleware action |
| `warn` | Allowed | Log + metric `legacy_write_attempt` |
| `block` | **Denied 409** | Problem Details + link v1 route |

### Headers (warn/block)

```
Deprecation: true
Sunset: Sat, 01 Jan 2028 00:00:00 GMT
Link: </v1/bookings>; rel="successor-version"
CoreFlow-Enforcement: block
```

### Quando bloquear

| Gate | Requirement |
|------|-------------|
| Staging block | 12/12 paridade PASS + 7 days flag ON |
| Production block | Staging block 14 days + zero P1 |

### Quando avisar (warn)

Default all environments until F6. Production stays `warn` until production block gate.

### Quando retornar 410 Gone

| Milestone | Routes |
|-----------|--------|
| R4 | All legado booking routes |
| R5 | Remaining legado writes |
| Never R2 | — |

### Quando remover legado (code)

| Milestone | Action |
|-----------|--------|
| R3-F2 | Remove ReservationService booking delegation |
| R3-F3 | Remove booking legado routers |
| R4 | Remove agendamentos model |

### Métrica gate (corrigida)

| Métrica | R2-F6 threshold |
|---------|-----------------|
| Booking write paridade | 100% |
| Global legacy write % | Informativo only — **not** gate R2 |
| `legacy_write_attempt` on blocked routes | 0 in staging 48h before prod |

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Block all legado writes | ❌ Quebra piloto |
| B | Block booking writes only | ✅ Escolhida |
| C | Warn forever | ❌ No sunset progress |

## Consequências

- F6 staging block only booking narrow
- Production block R3-F1
- 70% global writes removed as R2 success criterion (RFC-003 S11 uses booking-specific)

## Referências

- RFC-002
- `docs/architecture/LegacyToCoreRouteMap.md`
- `docs/architecture/R2-ParityMatrix.md`
