# ADR-031 — Idempotency, Version & Optimistic Concurrency

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-024, ADR-025, ADR-026 |

---

## Contexto

Dual-write e retries HTTP exigem idempotência. Approve/reject concorrentes exigem controle de concorrência.

## Decisão

### Idempotency-Key (POST mutating)

| Endpoint | Required | Storage |
|----------|----------|---------|
| `POST /v1/bookings` | ✅ Mandatory F1b | `idempotency_keys` table |
| `POST /v1/bookings/{id}/approve` | ✅ Recommended | same |
| `POST /v1/bookings/{id}/reject` | ✅ Recommended | same |
| `POST /v1/bookings/{id}/cancel` | ✅ Recommended | same |

**Header:** `Idempotency-Key: {uuid-v4}` (client generated)

**Behavior:**

| Case | Response |
|------|----------|
| First request | Process normally; store `(key, company_id, response_body_hash, booking_id)` TTL 24h |
| Duplicate same key + same body | Return cached response `200` with same body |
| Duplicate same key + different body | `409` Problem Details `idempotency_key_reused` |
| Missing key on create | `400` Problem Details `idempotency_key_required` |

### Version (Optimistic Lock)

| Field | Location | Increment |
|-------|----------|-----------|
| `version` | `core_bookings.version` INT | Every state transition |

**Update pattern:**

```
UPDATE core_bookings SET ..., version = version + 1
WHERE id = :id AND company_id = :cid AND version = :expected_version
```

If rows affected = 0 → `409 Conflict` Problem Details `version_conflict`.

### ETag

| Endpoint | Header |
|----------|--------|
| `GET /v1/bookings/{id}` | `ETag: W/"{version}"` |
| `POST approve/reject/cancel` | Optional `If-Match: W/"{version}"` |

If `If-Match` mismatch → `412 Precondition Failed`.

### Retries

| Client | Safe? | Condition |
|--------|-------|-----------|
| Retry POST create | ✅ | Same Idempotency-Key |
| Retry approve | ✅ | Same Idempotency-Key or If-Match |
| Retry without key | ❌ | May duplicate — blocked on create |

### Conflict Resolution

| Conflict | Resolution |
|----------|------------|
| Version conflict | Client refresh GET + retry with new version |
| Slot conflict (scheduling) | 409 `slot_unavailable` — client pick new slot |
| Idempotency reuse | Client must generate new key |

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Pessimistic lock only | ❌ Throughput |
| B | Optimistic version + ETag | ✅ Escolhida |
| C | No concurrency control | ❌ Data corruption |

## Consequências

- F1b implements idempotency store + OpenAPI doc
- F2 implements version on approve/reject
- FF-API-005, FF-API-007

## Referências

- `docs/APIGovernance.md`
- ADR-024
