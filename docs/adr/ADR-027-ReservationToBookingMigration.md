# ADR-027 — Migration Reservation → Booking Events

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-009, RFC-009 |

---

## Contexto

Event catalog contém `reservation.created` (legado) e documentação v3 assume `booking.created`. Consumidores precisam de estratégia de coexistência.

## Decisão

### Nomenclatura canônica (Core)

| Legado | Canônico | Status R2 |
|--------|----------|-----------|
| `reservation.created` | `booking.created` | Alias dual-publish F1b |
| `reservation.updated` | `booking.updated` | Alias F1b |
| `reservation.approved` | `booking.approved` | Alias F2 |
| `reservation.rejected` | `booking.rejected` | Alias F2 |
| `reservation.cancelled` | `booking.cancelled` | Alias F2b |

### Coexistência (F1b → R3-F2)

**Dual-publish temporário** quando `FEATURE_BOOKING_CORE_ENABLED=true`:

1. Outbox insere **primário:** `booking.created`
2. Outbox insere **alias:** `reservation.created` (mesmo payload + `deprecated_alias: true`)

Consumidores novos: subscribe `booking.*` only.

Consumidores legados: continue `reservation.*` until migrated.

### Event envelope (ambos)

```json
{
  "event_type": "booking.created",
  "event_version": "v1",
  "aggregate_id": "uuid",
  "aggregate_type": "booking",
  "company_id": "uuid",
  "correlation_id": "uuid",
  "occurred_at": "ISO8601",
  "payload": { }
}
```

Alias `reservation.created` includes header `canonical_type: booking.created`.

### Backward compatibility

| Rule | Detail |
|------|--------|
| Payload fields | Superset — no remove until R4 |
| Avro schema | Additive MINOR only |
| New consumers | MUST use `booking.*` |

### Sunset schedule

| Release | Ação |
|---------|------|
| R2-F1b | Dual-publish begins |
| R3-F1 | WARN log on reservation.* consumption |
| R3-F2 | ✅ Implemented (`2.2.0-r3-f2`) — Stop alias publish |
| R4 | Remove reservation.* from catalog; 410 on subscribe |

### Flag OFF path

Legado path continues `reservation.*` only — no `booking.*` until flag ON.

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Big-bang rename | ❌ Quebra consumers |
| B | Dual-publish alias | ✅ Escolhida |
| C | Forever both names | ❌ Dívida permanente |

## Consequências

- Event catalog updated F0
- FF-EVT-005 validates booking.created on core path

## Referências

- `docs/EventDrivenArchitecture.md`
- `docs/architecture/EventCatalog.md`
