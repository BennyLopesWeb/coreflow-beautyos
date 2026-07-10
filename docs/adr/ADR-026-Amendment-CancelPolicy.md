# ADR-026 Amendment — Cancel Policy (R2-F2b)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Accepted (tech) — D6 PASS 2026-07-09 |
| **Data** | 2026-07-09 |
| **Amends** | [ADR-026 — Booking State Machine](./ADR-026-BookingStateMachine.md) |
| **Sign-off** | [R2-F2b-CancelPolicy-Signoff.md](../reviews/R2-F2b-CancelPolicy-Signoff.md) |

---

## Contexto

R2-F2b implementa `CancelBooking` no core path com policy para `approved → cancelled`.

## Decisão

### Transição `approved → cancelled`

| Regra | Valor |
|-------|-------|
| Boundary | `starts_at - now >= 24h` (inclusive no limite exato de 24h) |
| Equivalente | `allowed = now_utc <= starts_at_utc - timedelta(hours=24)` |
| Violação | HTTP `409 cancel_policy_violation` |

### Transição `pending → cancelled`

Sempre permitida no core path (actor authorized).

### Estados terminais

`rejected`, `cancelled` — sem outbound transitions (SM-2).

### CancelPolicyPort

Policy de negócio externa ao aggregate:

- `may_cancel(booking, clock) -> bool`
- Aggregate `Booking.cancel()` valida apenas lifecycle (pending | approved → cancelled)

### Datetime e Clock

> All comparisons used by `CancelPolicyPort` must be performed with timezone-aware UTC datetimes. Naive datetimes are invalid inputs and must be normalized by the adapter or rejected with a validation error before policy evaluation.

- **Clock / TimeProvider** injetado — sem `datetime.now()` no aggregate.
- Comparações em UTC após normalização.

### Divergência controlada (migração)

| Path | Comportamento |
|------|---------------|
| Flag OFF | `ReservationService.cancelar()` — permissivo (P07 regressão zero) |
| Flag ON | Policy 24h para approved (P07 divergência intencional) |

### Eventos

- `booking.cancelled`
- `reservation.cancelled` (alias ADR-027)
- Payload: `booking_id`, `correlation_id`, `version`, `reason`

### Verificação

Paridade **P06**, **P07** — [R2-ParityMatrix](../architecture/R2-ParityMatrix.md).

---

## Consequências

- Accepted após validação F2b em CI/staging
- Idempotency-Key cancel: **optional** F2b (Q5)

## Referências

- [R2-F2b.md](../sprints/R2-F2b.md)
- ADR-025, ADR-028 (pattern), ADR-031
