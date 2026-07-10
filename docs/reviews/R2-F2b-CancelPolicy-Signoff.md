# R2-F2b — Cancel Policy Sign-off

**Documento:** `docs/reviews/R2-F2b-CancelPolicy-Signoff.md`  
**Versão:** 1.2 · **Data:** 2026-07-09  
**Sprint:** R2-F2b · **Escopo:** §7 [R2-F2b.md](../sprints/R2-F2b.md)  
**Status:** ✅ **Approved for implementation** · **Implementation:** ✅ **AUTHORIZED**

---

## Context

R2-F2b introduces **Booking cancellation** in the Core lifecycle.

Decision under review:

- `pending` booking can always be cancelled
- `approved` booking requires cancellation policy validation
- `rejected` / `cancelled` bookings are terminal states (core path)

**Governança:** este checklist valida regra de negócio e prontidão para implementação.  
**ADR-026 amendment** somente **após** aceite aqui, se a decisão for consolidada como arquitetura permanente.

```
R2-F2b.md §7 Cancel Policy
        │
        v
Platform Lead Sign-off (este doc) ✅
        │
        v
ADR-026 amendment (se necessário)
        │
        v
Implementação F2b
```

---

## Domain Transition Matrix

| Source State | `cancel()` | Rule | Approved |
|--------------|------------|------|----------|
| `pending` | YES | Always allowed | ☐ |
| `approved` | CONDITIONAL | Policy ≥24h before slot (ver § Time calculation) | ☐ |
| `rejected` | NO | Terminal state (SM-2) | ☐ |
| `cancelled` | NO | Idempotent conflict or return current state | ☐ |

---

## Time Calculation (approved booking policy)

**Must be signed before P07 tests are written.**

### Regra normativa (proposta T1)

**≥ 24h before slot** — tempo restante até `starts_at`:

| Tempo restante | Resultado |
|----------------|-----------|
| **24h 00m** (exato) | **ALLOWED** |
| **> 24h** | **ALLOWED** |
| **< 24h** (ex.: 23h 59m) | **BLOCKED** (`409 cancel_policy_violation`) |

Equivalente: `allowed = now <= starts_at - timedelta(hours=24)` (boundary **inclusive** no limite de 24h exatos).

### Reference example

| Field | Value |
|-------|-------|
| Slot `starts_at` | `2026-07-10 15:00` |
| Cancel attempt `now` | `2026-07-09 15:01` |
| Tempo restante | 23h 59m → **BLOCKED** (< 24h) |

| Cancel attempt `now` | Tempo restante | Resultado (T1 ≥ 24h) |
|----------------------|----------------|----------------------|
| `2026-07-09 15:00` | 24h 00m | **ALLOWED** |
| `2026-07-09 14:59` | 24h 01m | **ALLOWED** |
| `2026-07-09 15:01` | 23h 59m | **BLOCKED** |

### Decisions for sign-off

| # | Decision | Options | Approved choice |
|---|----------|---------|-----------------|
| T1 | **Boundary** | `≥ 24h` (inclusive) · `> 24h` (strict) | ☐ `≥ 24h` · ☐ `> 24h` |
| T2 | **Timezone** | UTC · Tenant/business TZ · Same TZ as `starts_at` | ☐ UTC (recommended) |
| T3 | **Comparison implementation** | `now_utc <= starts_at_utc - 24h` | ☐ |
| T4 | **Naive datetime guard** | Adapter **must not** compare naive datetimes; normalize or reject | ☐ |

**Recommendation (Platform review):**

- **T1:** `≥ 24h` inclusive — `starts_at - now >= 24h` / `now <= starts_at - timedelta(hours=24)`.
- **T2:** Normalizar `now` e `starts_at` para **UTC** antes da comparação.
- **T3:** `CancelPolicyPort.may_cancel()` retorna `False` quando `(starts_at - now) < 24h`.
- **T4:** No adapter — `assert starts_at.tzinfo is not None` ou normalização obrigatória; nunca comparar datetime naive.

Approved: ☐

---

## Compatibility Decision

### Legacy path

**Flag OFF:** `ReservationService.cancelar()`

Current behavior:

- permissive cancellation (any source state)
- no 24h policy enforcement
- releases schedule + soft-delete

Decision:

- [x] **Keep legacy behavior unchanged** (proposed — confirm below)

Reason: migration compatibility; P07 flag OFF = regressão zero.

Approved: ☐

---

### Core path

**Flag ON:** `Booking.cancel()` + `CancelPolicyPort.may_cancel()`

Decision:

- [x] **Apply ADR-026 cancellation rules** (proposed — confirm below)
- Divergence from legacy on `approved` cancel window is **intentional** (flag ON only)

Approved: ☐

---

## Architecture Validation

### Q1 — Policy ownership

**Question:** Where does the 24h rule live?

**Decision:** Application/domain policy through `CancelPolicyPort` (not inside Payment or Scheduling ORM).

Approved: ☐

---

### Q2 — Aggregate responsibility

**Question:** Should `Booking` decide if cancellation is allowed?

**Decision:**

- `Booking.cancel()` enforces **state transition** (SM-1 / SM-2)
- `CancelPolicyPort` validates **external/business constraints** (24h window for `approved`)

Approved: ☐

---

### Q3 — Transaction behavior

Cancellation must preserve in **one TX** (ADR-025):

- booking update (`save_with_version`)
- outbox event (`OutboxBatch.record`)
- legacy projection (`project_cancel_booking`)
- commit → `publish_after_commit()`

Approved: ☐

---

### Q4 — Compatibility

**Flag OFF** must preserve `ReservationService.cancelar()` behavior without regression.

Approved: ☐

---

### Q5 — Idempotency-Key on cancel

**Question:** Idempotency-Key mandatory on cancel?

**Context:** Create exige key (F1b). Approve/reject usam If-Match + version; Idempotency-Key é recommended.

**Decision (proposed for F2b):**

- **Optional** — não tornar obrigatório nesta sprint.
- Cancel já possui proteção natural: state transition + `version` + If-Match opcional.
- Retry após cancel bem-sucedido encontra estado terminal → domínio evita duplicação.

| Option | F2b |
|--------|-----|
| Optional (If-Match + version sufficient) | ☐ **Recommended** |
| Mandatory (align with create) | ☐ Defer — only if external retry semantics require |

Approved: ☐

---

### Q6 — Refund on cancel

**Question:** Automatic refund on cancel?

**Decision:** OUT of scope — R3 payment write path.

Approved: ☐

---

### Q7 — Clock source

**Question:** Qual relógio é usado para a comparação de policy (24h)?

**Decision (proposed):**

- Injetar **Clock / TimeProvider** — evitar `datetime.now()` direto no domínio ou no aggregate.
- Mantém padrão F2: aggregate → invariantes de estado; ports → dependências externas (policy, relógio).

```
BookingDomainService.cancel()
        │
        ├── CancelPolicyPort.may_cancel(booking, clock)
        │
        └── Clock / TimeProvider → UTC comparison
```

Implementação concreta pode usar UTC do sistema inicialmente; governança exige abstração explícita.

Approved: ☐

---

## ADR-026 amendment — status e conteúdo esperado

**Não redigir amendment até sign-off preenchido.**

| Situação | Ação |
|----------|------|
| Sign-off não preenchido | 🚫 Não redigir amendment |
| Sign-off com **Changes requested** | 🟡 Revisar sprint/sign-off primeiro |
| **Approved for implementation** | ✅ Redigir draft ADR-026 amendment |
| Implementação concluída e validada | ✅ Marcar amendment Accepted |

### Conteúdo esperado do futuro amendment

1. Transição `approved → cancelled` condicionada por policy.
2. Boundary exato (≥ 24h inclusive, se aprovado em T1).
3. Comparação em UTC com datetimes timezone-aware (T2, T4).
4. `CancelPolicyPort` como abstração de política.
5. Divergência controlada flag OFF vs flag ON durante migração.
6. Referência a P06 e P07 na matriz de verificação.

### Texto normativo proposto (T2/T4 — para incluir no amendment)

> All comparisons used by `CancelPolicyPort` must be performed with timezone-aware UTC datetimes. Naive datetimes are invalid inputs and must be normalized by the adapter or rejected with a validation error before policy evaluation.

Elimina ambiguidade sobre: horário local do servidor, timezone do tenant, DST, datetime naive do ORM ou da API.

---

## Post sign-off actions

| # | Action | Owner | When |
|---|--------|-------|------|
| 1 | Mark DoR D5 ✅ in [R2-F2b.md](../sprints/R2-F2b.md) + [Gate](./R2-F2b-Gate.md) | Platform Lead | On approval |
| 2 | Redigir **ADR-026 amendment** (conteúdo § acima) | Platform Team | After **Approved for implementation** |
| 3 | Begin F2b implementation | Dev | After amendment draft + D5 ✅ |

---

## Final Approval

| Field | Value |
|-------|-------|
| **Platform Lead** | |
| **Date** | |
| **Decision** | ☑ **Approved for implementation** · ☐ **Changes requested** |

**Platform Lead:** Platform Team (checkpoint chat) — **provisional**; ratificação formal pendente  
**Date:** 2026-07-09

**Decisões consolidadas:** T1 ≥24h inclusive · T2 UTC · T4 naive guard · Q5 optional · Q6 OUT · Q7 Clock/TimeProvider

**Pós-implementação:** código e CI (305 PASS) verificados 2026-07-09. Sign-off **não** substitui D6 staging nem ADR **Accepted** — ver [R2-F2b-D6-Staging.md](./R2-F2b-D6-Staging.md).

---

## Referências

- [R2-F2b.md](../sprints/R2-F2b.md) §7
- [ADR-026](../adr/ADR-026-BookingStateMachine.md)
- [R2-ParityMatrix](../architecture/R2-ParityMatrix.md) — P06, P07
- [R2-F2 Gate Review](./R2-F2-GateReview.md)
