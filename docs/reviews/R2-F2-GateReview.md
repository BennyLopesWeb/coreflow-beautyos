# R2-F2 — Gate Review

**Documento:** `docs/reviews/R2-F2-GateReview.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Sprint:** R2-F2 · **Versão código:** `1.20.0-r2-f2`  
**Veredito:** ✅ **ACCEPTED (tech)**

---

## Contexto

Revisão formal pós-implementação antes de iniciar **R2-F2b**. Complementa DoD §15 de [R2-F2.md](../sprints/R2-F2.md).

| Métrica | Valor |
|---------|-------|
| Testes CI | **297 passed**, 6 skipped |
| Incremento vs R2-F1b | +12 testes (`test_r2_f2_booking_approve_reject.py`) |
| Baseline anterior | 285 passed (R2-F1b) |

---

## Validated

| # | Item | ADR / artefato | Evidência |
|---|------|----------------|-----------|
| V1 | TD-R2-F1b-001 resolvido — `OutboxBatch` + defer_commit | ADR-025 | `outbox.py`, create/approve/reject core path |
| V2 | State machine approve/reject no aggregate | ADR-026 SM-1/SM-2 | `Booking.approve()`, `Booking.reject()` |
| V3 | Optimistic lock + ETag + If-Match | ADR-031 | `save_with_version`, router `412`/`409` |
| V4 | PaymentQueryPort — zero acoplamento ORM payment | ADR-028 | `LegacyPaymentQueryAdapter` |
| V5 | Dual-write approve/reject flag ON | ADR-024/025 | `project_approve_booking`, `project_reject_booking` |
| V6 | Eventos lifecycle + alias + correlation + version | ADR-027 | `booking.approved/rejected`, `reservation.*` |
| V7 | Paridade P03–P05, P08 ON + OFF | [R2-ParityMatrix](../architecture/R2-ParityMatrix.md) | `test_r2_f2_*`, `test_cf8` (P03 legacy) |
| V8 | Rollback TX — outbox não processed | ADR-025 | `test_defer_commit_rollback_on_approve_projection_failure` |
| V9 | POST create congelado (F1/F1b) | Governança R2 | Escopo OUT respeitado |
| V10 | FF-BKG-001 / FF-PAY-001 | Fitness functions | `test_r2_f0_5_acl_wiring.py` |
| V11 | Métricas approve/reject/defer_commit | Sprint §13 | `ArchitectureMetricsStore` |

---

## Riscos fechados nesta sprint

| Risco anterior | Resultado |
|----------------|-----------|
| Commit interno Outbox (TD-R2-F1b-001) | ✅ Resolvido (core path) |
| Ausência de transição de estado no domínio | ✅ Resolvido |
| Concorrência de atualização | ✅ Optimistic lock |
| Acoplamento Booking → Payment | ✅ PaymentQueryPort |
| Falta de eventos lifecycle approve/reject | ✅ Resolvido |
| Divergência Core/Legacy approve-reject | ✅ Paridade validada |

---

## Known limitation (aceito para migração)

| ID | Descrição | Severidade | Owner |
|----|-----------|------------|-------|
| **TD-R2-F2-001** | Legacy approve/reject ainda usa `record_and_publish()` (commit interno outbox) | 🟢 Baixa | R2-F2b opcional |
| **TD-R2-F2-002** | `_to_domain` usa duração default 30min até offering duration no load | 🟡 Média | R2-F3b / catalog port |

**Mitigação TD-R2-F2-001:** paridade flag OFF PASS; core path usa OutboxBatch; alinhar legacy handlers em F2b se ARB decidir.

---

## Correção destacada

**Persistence → domain mapping:** `TimeSlot.ends_at = starts_at + 30min` em `CoreBookingRepository._to_domain()`. Falha silenciosa na reconstrução do aggregate (banco correto, load inválido). Capturada por P03–P05.

---

## Riscos residuais pós-gate

| Área | Estado |
|------|--------|
| Approve/reject domain | ✅ |
| Optimistic locking | ✅ |
| Outbox atomicity (core) | ✅ |
| Outbox atomicity (legacy approve/reject) | 🟡 TD-R2-F2-001 |
| Cancel domain | 🔒 R2-F2b |
| Paridade 12/12 | 🔒 R2-F2b (8/12 hoje) |
| Staging F2 48h flag ON | 🟡 operacional |
| Governança D4/D5/D6 | 🟡 operacional |

---

## Gate para R2-F2b

| # | Critério | Status |
|---|----------|--------|
| G1 | P03–P05, P08 PASS CI | ✅ |
| G2 | DoD F2 §15 completo | ✅ |
| G3 | Sprint doc R2-F2b | ✅ [R2-F2b.md](../sprints/R2-F2b.md) + [Sign-off](../reviews/R2-F2b-CancelPolicy-Signoff.md) |
| G4 | Regras cancel definidas (ADR-026) | ☐ — [Cancel Policy Sign-off](../reviews/R2-F2b-CancelPolicy-Signoff.md) |
| G5 | Staging approve/reject 48h (recomendado) | ☐ operacional |

**Próximo incremento:** `cancel()` + P06, P07 → paridade **12/12**.

---

## Veredito

✅ **ACCEPTED (tech)** — merge autorizado do ponto de vista de arquitetura e testes. Governança operacional (staging, sign-off) não bloqueia branch/PR técnico.

---

**Referências:** [R2-F2.md](../sprints/R2-F2.md) · [R2-F1b Gate Review](./R2-F1b-GateReview.md) · [ADR-026](../adr/ADR-026-BookingStateMachine.md)
