# ADR-025 — Transaction Boundaries (Booking)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-024, ADR-028, ADR-029 |

---

## Contexto

Booking create envolve scheduling, persistência, sync legado e outbox. Sem fronteiras explícitas, falhas parciais corrompem SoT.

## Decisão — Sequência explícita: Booking Create

### Fluxo completo (flag ON)

```
[HTTP] POST /v1/bookings
  │
  ▼
(1) API Layer — validate DTO, extract Idempotency-Key, correlation_id
  │
  ▼
(2) Application — CreateBookingHandler
  │    ├─ IdempotencyStore.check(key) → return cached if exists
  │    ├─ CatalogQueryPort.get_offering(offering_id)
  │    ├─ CustomerQueryPort.get_customer(customer_id)
  │    └─ SchedulingPort.check_availability(resource_id, worker_id, slot)
  │
  ▼
(3) Domain — Booking.create(...) — invariantes, BookingCreated event (in-memory)
  │
  ▼
(4) BEGIN TRANSACTION (isolation: READ COMMITTED)
  │    ├─ (4a) CoreBookingRepository.save(booking)
  │    ├─ (4b) LegacyBookingPort.project_create(booking) → agendamentos
  │    ├─ (4c) OutboxRepository.insert(booking.created envelope)
  │    └─ (4d) IdempotencyStore.save(key, booking_id, response_hash)
  │
  ▼
(5) COMMIT
  │
  ▼
(6) [Async] Outbox worker → publish booking.created → bus
  │
  ▼
(7) [Async] Plugin hooks booking.created
```

### Atomicidade

| Escopo | Atomic? | Mecanismo |
|--------|---------|-----------|
| Steps 4a–4d | ✅ Sim | Single PostgreSQL transaction |
| Step 2 queries | ❌ Pre-TX | Read-only; retry on conflict |
| Step 6 publish | ❌ Post-TX | Outbox pattern — at-least-once |
| Step 7 hooks | ❌ Post-TX | Async; DLQ on failure |

### Isolation

- **READ COMMITTED** default PostgreSQL
- Optimistic lock on approve/reject: `UPDATE ... WHERE version = :expected`
- Scheduling conflict: unique constraint `(resource_id, starts_at, ends_at)` where status active

### Consistency

- **Strong consistency** core+legacy within TX (ADR-024)
- **Eventual consistency** outbox → bus (seconds)
- **Eventual consistency** read models (R3)

### Approve / Reject sequence

```
(1) Load booking FOR UPDATE (row lock)
(2) PaymentQueryPort.is_deposit_confirmed(booking_id) — approve only
(3) Domain transition approve()/reject()
(4) BEGIN TX
    (4a) Repository.save
    (4b) LegacyBookingPort.project_update
    (4c) Outbox insert booking.approved/rejected
(5) COMMIT
(6) Async publish + hooks
```

### Cancel sequence (F2b)

Same as approve; no payment check; allowed states per ADR-026.

### Falhas parciais

| Falha em | Comportamento |
|----------|---------------|
| Step 2 scheduling unavailable | 503; no TX |
| Step 2 slot conflict | 409 Problem Details; no TX |
| Step 4b legacy projection | ROLLBACK; 500; no orphan core |
| Step 4c outbox insert fail | ROLLBACK |
| Step 6 publish fail | Retry worker; data consistent |
| Step 7 hook fail | DLQ; booking committed |

### Retries

| Layer | Retry |
|-------|-------|
| HTTP client | Idempotency-Key safe retry |
| Outbox worker | 5x exponential backoff |
| SchedulingPort | 1 retry on transient DB error |

### Compensações

**Não usar Saga distribuída R2** — monolith single DB. Compensação = ROLLBACK TX.

Post-commit failures (outbox/hooks) → reconciliation + manual replay — **não** delete booking.

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Saga cross-service | ❌ Prematuro |
| B | Single TX core+legacy+outbox | ✅ Escolhida |
| C | Core TX then async legacy | ❌ Drift risk |

## Consequências

- LegacyBookingPort must participate in same UnitOfWork
- Outbox mandatory before event consumers
- Tests must verify rollback on projection failure

## Referências

- `docs/EventDrivenArchitecture.md`
- ADR-024
