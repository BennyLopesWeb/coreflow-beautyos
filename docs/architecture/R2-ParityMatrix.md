# R2 — Matriz de Paridade (Booking)

**Documento:** `docs/architecture/R2-ParityMatrix.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Normativo — gate de merge R2-F2b+  
**RFC:** [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md)

---

## Regras

- Cada cenário deve PASS com `FEATURE_BOOKING_CORE_ENABLED=true` **e** `false` (regressão).
- Comparar: HTTP status, body fields críticos, DB state, outbox events.
- Test file pattern: `tests/test_core/test_r2_parity_*.py`

---

## Matriz (12 cenários)

| # | Cenário | Legado | v1 Core | Validações | Fase |
|---|---------|--------|---------|------------|------|
| P01 | **Create** booking básico | `POST /agendamentos` | `POST /v1/bookings` | status pending; legacy_id set; `booking.created` + alias; Idempotency-Key | F1, F1b |
| P02 | **Create** slot indisponível | `POST /agendamentos` | `POST /v1/bookings` | 409 slot_unavailable; no DB row | F1 |
| P03 | **Approve** com sinal pago | admin approve flow | `POST /v1/bookings/{id}/approve` | status approved; `booking.approved`; workflow intact | F2 |
| P04 | **Approve** sem sinal | admin approve | `POST .../approve` | 409 deposit_required | F2 |
| P05 | **Reject** pending | admin reject | `POST .../reject` | status rejected; `booking.rejected` | F2 |
| P06 | **Cancel** pending | cancel legado | `POST .../cancel` | status cancelled; `booking.cancelled` | F2b |
| P07 | **Cancel** approved (policy) | cancel legado | `POST .../cancel` | cancelled OR 409 per policy | F2b |
| P08 | **Deposit confirmed** → workflow | webhook payment | `POST /v1/payments` | `payment.deposit.confirmed`; enables approve | F2 |
| P09 | **Conflict** double booking same slot | two creates | two POST | second 409; first intact | F1 |
| P10 | **Waitlist → booking** | fila promote | waitlist hook + create | booking created; plugin hook fired | F4 |
| P11 | **Resource indisponível** | tranca/cadeira busy | create with resource_id | 409; scheduling port invoked | F3 |
| P12 | **Retry** idempotent create | retry POST | same Idempotency-Key | same booking_id; single row | F1b |

---

## Campos comparados (create)

| Campo | Legado | Core |
|-------|--------|------|
| Status | `pendente` | `pending` |
| Customer ref | `cliente_id` | `customer_id` |
| Slot | `data_inicio/fim` | `starts_at/ends_at` |
| Legacy link | `id` | `legacy_id` |
| Tenant | `empresa_id` | `company_id` |

---

## Eventos esperados

| Cenário | Eventos outbox |
|---------|----------------|
| P01 | `booking.created`, `reservation.created` (alias) |
| P03 | `booking.approved` |
| P05 | `booking.rejected` |
| P06 | `booking.cancelled` |
| P08 | `payment.deposit.confirmed` |

---

## Critério gate

| Fase | Cenários obrigatórios |
|------|----------------------|
| F1 merge | P01, P02, P09 |
| F1b merge | P01, P12 |
| F2 merge | P03, P04, P05, P08 |
| F2b merge | P06, P07 + all above |
| F3 merge | P11 |
| F4 merge | P10 |
| F6 release | **12/12 PASS** |

---

## Referências

- `tests/test_cf8_workflow_ai_enforcement.py`
- ADR-024, ADR-026, ADR-027
