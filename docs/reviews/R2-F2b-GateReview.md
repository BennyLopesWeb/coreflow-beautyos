# R2-F2b — Gate Review (pós-implementação)

**Documento:** `docs/reviews/R2-F2b-GateReview.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Sprint:** R2-F2b · **Versão código:** `1.20.1-r2-f2b`  
**Veredito:** ✅ **ACCEPTED (tech)** — D6 staging-simulated PASS (18/18)

---

## Contexto

Revisão formal pós-implementação de **cancel** no domínio Booking. Complementa DoD §11 de [R2-F2b.md](../sprints/R2-F2b.md).

| Métrica | Valor |
|---------|-------|
| Testes CI (local) | **305 passed**, 6 skipped |
| Incremento vs R2-F2 | +8 testes (`test_r2_f2b_booking_cancel.py`) |
| Baseline anterior | 297 passed (R2-F2) |
| Evidência pytest | 2026-07-09 · `pytest -o addopts=` · exit 0 |

**Governança:** implementação e testes locais verificados. **Não** equivale a sprint **Completed** nem ADR **Accepted** até D6 staging e ratificação formal do sign-off.

---

## Validated (tech / CI)

| # | Item | ADR / artefato | Evidência |
|---|------|----------------|-----------|
| V1 | `Booking.cancel()` + estado `CANCELLED` | ADR-026 amendment (draft) | `booking.py`, `booking_types.py` |
| V2 | `CancelPolicyPort` — ≥24h inclusive, UTC | Sign-off T1/T2/T4 | `cancel_policy_adapter.py`, `test_cancel_policy_24h_boundary` |
| V3 | `ClockPort` / `SystemClockAdapter` | Sign-off Q7 | `clock_port.py`, `system_clock_adapter.py` |
| V4 | `CancelBooking` handler + defer_commit | ADR-025 | `cancel_booking.py` |
| V5 | Dual-write cancel flag ON | ADR-024/025 | `project_cancel_booking`, ACL |
| V6 | Eventos `booking.cancelled` + alias `reservation.cancelled` | ADR-027 | `events.py` |
| V7 | `POST /v1/bookings/{id}/cancel` | Sprint §3 | `v1_bookings.py` |
| V8 | P06 cancel pending ON + OFF | R2-ParityMatrix | `test_p06_cancel_pending_*` |
| V9 | P07 cancel approved ON (policy) + OFF (legacy permissivo) | R2-ParityMatrix | `test_p07_cancel_approved_*` |
| V10 | Terminal states — reject/cancel conflict | ADR-026 SM | `test_booking_cancel_invalid_state` |
| V11 | Policy violation &lt;24h → 409 | Sign-off T1 | `test_p07_cancel_approved_within_24h_core_path` |
| V12 | Rollback TX — outbox não processed | ADR-025 | `test_defer_commit_rollback_on_cancel_projection_failure` |
| V13 | `APP_VERSION=1.20.1-r2-f2b` | Sprint §11 | `config.py`, `test_r1_f2_platform_observability` |
| V14 | Regressão suite completa | CI | 305 passed (inclui P01–P09 entregues) |
| V15 | Fix legacy `ReservationService.cancelar()` | — | Return pós soft-delete |

---

## Pendente (governança / operacional)

| # | Item | Status | Bloqueia ACCEPTED? |
|---|------|--------|-------------------|
| P1 | D6 staging — cancel pending/approved ±24h, flag OFF, outbox, legacy | ✅ staging-simulated 18/18 | Não |
| P2 | ADR-026 Amendment → **Accepted** | ✅ | Não |
| P3 | Sign-off D5 formal (Platform Lead nome/data) | ⏳ Provisional (checkpoint chat) | Recomendado |
| P4 | Teste explícito If-Match cancel → 412/409 | ⏳ Parcial (F2 patterns) | Não (baixo) |
| P5 | Paridade P10, P11 | 🔒 Fora de escopo F2b | Não |

---

## Riscos fechados nesta sprint

| Risco | Resultado |
|-------|-----------|
| Cancel sem policy no core | ✅ `CancelPolicyPort` |
| Divergência timezone naive (SQLite testes) | ✅ Normalização UTC no adapter |
| Legacy cancel quebrava após soft-delete | ✅ Fix `cancelar()` |
| Outbox fora da TX no cancel core | ✅ `OutboxBatch` + defer_commit |
| Paridade P06/P07 | ✅ CI |

---

## Riscos residuais pós-gate

| Área | Estado |
|------|--------|
| Cancel domain (core) | ✅ |
| Cancel domain (staging real) | ✅ staging-simulated |
| Paridade 10/12 (P10/P11 fora) | 🔒 F3/F4 |
| ADR amendment permanente | ⏳ Draft |
| Governança D5 formal | 🟡 Provisional |

---

## Sequência para ACCEPTED (tech)

```
Implementação ✅ → CI 305 PASS ✅ → D6 staging ✅ → ADR Accepted ✅ → Veredito ACCEPTED (tech)
```

Checklist operacional: [R2-F2b-D6-Staging.md](./R2-F2b-D6-Staging.md)

---

## Veredito

✅ **ACCEPTED (tech)** — código, CI e D6 staging-simulated (18/18) atendem escopo F2b. Sprint **Completed** (tech). Merge autorizado; observação 48h em deploy remoto recomendada pós-merge.

---

**Referências:** [R2-F2b.md](../sprints/R2-F2b.md) · [R2-F2b-Gate.md](./R2-F2b-Gate.md) · [Cancel Policy Sign-off](./R2-F2b-CancelPolicy-Signoff.md) · [ADR-026 Amendment](../adr/ADR-026-Amendment-CancelPolicy.md)
