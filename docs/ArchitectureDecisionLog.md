# CoreFlow — Architecture Decision Log

**Documento:** `docs/ArchitectureDecisionLog.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Propósito:** Changelog cronológico **apenas de decisões arquiteturais** (RFC, ADR, gates de release)  
**Índice detalhado:** `docs/ArchitectureDecisionIndex.md`

---

## Como usar

- Entradas **mais recentes no topo**
- Uma linha por evento significativo
- Não substituir ADRs — este log é índice temporal
- Atualizar em: aprovação RFC, aceite ADR, GO/NO-GO release, supersede

---

## 2026-07-16 — R3-F2 Remove ReservationService booking path delegation

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R3-F2 Remove booking legado | Commands core-only, ACL `*_via_legacy` fail-fast, `ReservationService` writes removidos, `2.2.0-r3-f2` |
| **Sunset** | ADR-027 alias `reservation.*` | Outbox para de publicar aliases; factories mantidas com `logger.warning` até R4 |
| **Amended (default)** | `FEATURE_BOOKING_CORE_ENABLED` | Default `true` — flag OFF passa a kill-switch sem fallback legado |
| **Published** | Release + sprint + gate | [2.2.0-r3-f2.md](releases/2.2.0-r3-f2.md) · [R3-F2.md](sprints/R3-F2.md) · [R3-F2-Gate.md](reviews/R3-F2-Gate.md) |

---

## 2026-07-20 — R4-F1 Legacy booking 410 Gone

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R4-F1 M6 | `LegacyGoneMiddleware` 410 + `reservation.created` catalog gone; `2.4.0-r4-f1` |
| **Published** | Release + gate | [2.4.0-r4-f1.md](releases/2.4.0-r4-f1.md) · [R4-F1-Gate.md](reviews/R4-F1-Gate.md) |

---

## 2026-07-21 — R4-F2 Disable booking legacy dual-write projection

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R4-F2 M7 | `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` default `false` — `project_*` (dual-write outbound ADR-024) deixa de ser chamado por padrão; `2.5.0-r4-f2` |
| **Published** | Release + gate | [2.5.0-r4-f2.md](releases/2.5.0-r4-f2.md) · [R4-F2-Gate.md](reviews/R4-F2-Gate.md) |

---

## 2026-07-20 — R3-F3 Remove legacy booking write routers

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R3-F3 M5 | Strip writes `/agenda` + `/reservations`; fila → CreateBookingHandler; `2.3.0-r3-f3` |
| **Published** | Release + gate | [2.3.0-r3-f3.md](releases/2.3.0-r3-f3.md) · [R3-F3-Gate.md](reviews/R3-F3-Gate.md) |

---

## 2026-07-16 — R3-F1 Enforcement expand + production pilot

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R3-F1 Enforcement expand | Block payments/fila + prod block (ADR-033 emenda), `2.1.0-r3-f1` |
| **Amended** | ADR-033 | Payments/fila passam a block; financeiro warn only |
| **Published** | Release + migration | [2.1.0-r3-f1.md](releases/2.1.0-r3-f1.md) · [legacy-payments-fila-to-v1.md](migrations/legacy-payments-fila-to-v1.md) |
| **Gated** | R3-F1 Gate | [R3-F1-Gate.md](reviews/R3-F1-Gate.md) |

---

## 2026-07-16 — R2-F6 Enforcement narrow + 2.0.0-beta.1

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R2-F6 Enforcement + beta | Block booking legado 409 (ADR-033), release `2.0.0-beta.1` |
| **Published** | Release notes + migration | [2.0.0-beta.1.md](./releases/2.0.0-beta.1.md) · [legacy-booking-to-v1.md](./migrations/legacy-booking-to-v1.md) |
| **Assessed** | PMM L2 partial ≥65% | [R2-PMM-L2-Partial.md](./reviews/R2-PMM-L2-Partial.md) |

---

## 2026-07-16 — R2-F5 Hardening (fitness + OTEL + reconciliation)

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R2-F5 Hardening | Fitness CI ERROR, span `booking.create.core`, reconciliation drift, `1.23.0-r2-f5` |
| **Published** | R2-F5 sprint + gate | [R2-F5.md](../sprints/R2-F5.md) · [R2-F5-Gate.md](../reviews/R2-F5-Gate.md) |

---

## 2026-07-16 — R2-F4 Plugin Engine + BeautyAgent + P10

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R2-F4 Plugin Engine | Typed HookRegistry, BeautyAgent em `app/plugins/beauty/`, P10, `1.22.0-r2-f4` |
| **Published** | R2-F4 sprint + gate | [R2-F4.md](../sprints/R2-F4.md) · [R2-F4-Gate.md](../reviews/R2-F4-Gate.md) |

---

## 2026-07-16 — R2-F3b Catalog/Customer repos + tiering emend

| Evento | Artefato | Notas |
|--------|----------|-------|
| **In progress / Implemented** | R2-F3b Catalog + Customer repositories | ADR-030 ports, ACL LegacyCatalog/Customer, TD-R2-F2-002, `1.21.1-r2-f3b` |
| **Emended** | ModuleTieringPolicy v1.1 | `catalog` + `customer` → CORE-SUPPORT (hexagonal lite); flatten Wave 2 catalog cancelado |
| **Published** | R2-F3b sprint doc | [R2-F3b.md](../sprints/R2-F3b.md) |

---

## 2026-07-16 — R2-F3 Resource Engine implemented (tech)

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R2-F3 Resource Engine | `modules/resource/`, CRUD `/v1/resources`, flag `resource.engine.enabled`, P11, `1.21.0-r2-f3` |
| **Accepted** | Sign-off §7 Resource Engine | Platform Lead via aprovação de implementação |
| **Updated** | R2-F3 Gate | [R2-F3-Gate.md](../reviews/R2-F3-Gate.md) — IMPLEMENTED |

---

## 2026-07-09 — R2-F3 sprint doc (governança)

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Published** | R2-F3 sprint doc | Resource Engine v1 — [R2-F3.md](../sprints/R2-F3.md) |
| **Published** | R2-F3 Gate v1.0 | [R2-F3-Gate.md](../reviews/R2-F3-Gate.md) |

---

## 2026-07-09 — R2-F2b D6 PASS + sprint fechada

| Evento | Artefato | Notas |
|--------|----------|-------|
| **D6 PASS** | R2-F2b staging harness | 18/18 cenários · [evidence](../evidence/R2-F2b-D6-staging-results.json) |
| **Accepted (tech)** | R2-F2b Gate Review | [R2-F2b-GateReview.md](../reviews/R2-F2b-GateReview.md) |
| **Accepted (tech)** | ADR-026 Amendment | Cancel Policy permanente |
| **Completed** | R2-F2b sprint | `1.20.1-r2-f2b` · 305 CI + 13 D6 harness |

---

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented (tech)** | R2-F2b | Cancel + CancelPolicyPort + Clock; P06/P07 CI; `1.20.1-r2-f2b`, **305 passed** |
| **Published** | R2-F2b Gate Review | [R2-F2b-GateReview.md](../reviews/R2-F2b-GateReview.md) — IMPLEMENTED, aceite pendente D6 |
| **Published** | R2-F2b D6 Staging checklist | [R2-F2b-D6-Staging.md](../reviews/R2-F2b-D6-Staging.md) |
| **Published** | R2-F2b PR prep | [R2-F2b-PR.md](../pull-requests/R2-F2b-PR.md) |
| **Draft** | ADR-026 Amendment Cancel Policy | Aguarda D6 → Accepted |
| **Pending** | Sprint Completed | Bloqueado por D6 + sign-off formal D5 |

---

## 2026-07-09 — R2-F2b implementação técnica

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Implemented** | R2-F2b cancel path | `cancel_booking.py`, ports, ACL, router, eventos |
| **Fixed** | ReservationService.cancelar | Return após soft-delete (obter excluía deleted) |
| **CI** | pytest suite | 305 passed, 6 skipped (2026-07-09) |

---

## 2026-07-09 — R2-F2b congelada (governança)

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Frozen** | R2-F2b | Doc package complete — implementation BLOCKED; aguardando D5 sign-off |
| **Published** | R2-F2b Gate v1.1 | [R2-F2b-Gate.md](../reviews/R2-F2b-Gate.md) |
| **Published** | Cancel Policy Sign-off v1.2 | Q7 Clock; ADR amendment workflow; T2/T4 normative text draft |

---

## 2026-07-09 — R2-F2 Approve/Reject domain

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Accepted (tech)** | R2-F2 | State machine approve/reject + defer_commit + optimistic lock; P03–P05/P08; `1.20.0-r2-f2`, 297 tests |
| **Published** | R2-F2 Gate Review | [R2-F2-GateReview.md](../reviews/R2-F2-GateReview.md) |
| **Published** | R2-F2b Gate | [R2-F2b-Gate.md](../reviews/R2-F2b-Gate.md) — implementation BLOCKED |
| **Published** | R2-F2b Cancel Policy Sign-off v1.1 | T1/T2/Q5 refinements — aguardando Platform Lead |
| **Published** | R2-F2b sprint doc | Cancel + paridade 12/12 — doc only, aguardando sign-off §7 |
| **Resolved** | TD-R2-F1b-001 | OutboxBatch + defer_commit — TX única create/approve/reject core path |

---

## 2026-07-09 — R2-F1b Gate Review ACCEPTED

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Accepted (tech)** | R2-F1b Gate Review | TD-R2-F1b-001 Outbox defer_commit → R2-F2 |
| **Published** | R2-F2 sprint doc | Approve/reject + state machine + PaymentQueryPort |

---

## 2026-07-09 — R2-F1b Idempotency & correlation

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Accepted (tech)** | R2-F1b | Idempotency-Key + correlation_id + P12 (`1.19.1-r2-f1b`, 285 tests) |

---

## 2026-07-09 — R2-F1b sprint doc + staging checklist

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Published** | R2-F1b sprint doc | Idempotency-Key + correlation_id + P12 — DoR aguarda staging F1 |
| **Published** | R2-F1-StagingValidation checklist | Fecha §18 F1; gates G2–G6 |

---

## 2026-07-09 — R2-F1 Booking create domain

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Accepted (tech)** | R2-F1 | Domain create + dual-write; paridade P01/P02/P09; pendências operacionais §18 |
| **Completed** | R2-F1 | `1.19.0-r2-f1`, 279 tests; bloqueador = schema drift SQLite (não arquitetura) |

---

## 2026-07-09 — Release 2 consolidation & GO

| Evento | Artefato | Notas |
|--------|----------|-------|
| **GO** | R2 Execution | ARB autoriza R2-F1 após DoR operacional |
| **Accepted** | ADR-033 | Enforcement block scope narrow |
| **Accepted** | ADR-032 | Feature flag lifecycle R2 |
| **Accepted** | ADR-031 | Idempotency & optimistic concurrency |
| **Accepted** | ADR-030 | Repository + ACL strategy |
| **Accepted** | ADR-029 | SchedulingPort evolution |
| **Accepted** | ADR-028 | Payment boundary |
| **Accepted** | ADR-027 | Reservation → booking events |
| **Accepted** | ADR-026 | Booking state machine |
| **Accepted** | ADR-025 | Transaction boundaries |
| **Accepted** | ADR-024 | Dual-write; Core SoT when flag ON |
| **Accepted** | ADR-011 | Plugin hook architecture |
| **Accepted** | ADR-010 | Resource Engine v1 meta model |
| **Accepted** | ADR-009 | Booking domain pure |
| **Approved** | RFC-003 | Core Domain Consolidation R2 |
| **Published** | R2-ExecutionPlan v4 | Sequência F0→F6 |
| **Completed** | R2-F0.5 | ACL wiring commands → ports (`1.18.5-r2-f0.5`) |
| **Published** | ArchitecturePrinciples | 15 princípios |
| **Published** | ReleaseGovernance | Fluxo oficial release |
| **Published** | DefinitionOfReady | DoR complementa DoD |
| **Published** | R2-ParityMatrix | 12 cenários |
| **Published** | SprintTemplate, R2-F1 sprint doc | Template + F1 operacional |
| **Verdict** | R2-ARB-FinalVerdict | **GO** (reavaliação stakeholder) |

---

## 2026-07-09 — Release 1 Foundation

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Completed** | R1-F2 | Platform health, ACL adapter, enforcement warn (`1.17.0-r1-f2`) |
| **Completed** | R1-F1 | Flags, event catalog, telemetria |
| **Accepted** | ADR-004–008 | Strangler, Core Framework, Plugin, Resource, Scheduling |
| **Approved** | RFC-002 | Core enforcement + sunset (c/ ACL) |
| **Approved** | RFC-001 | Governança arquitetural |
| **Accepted** | ADR-003 | Processo governança |
| **Accepted** | ADR-001, ADR-002 | Metamodelo + Beauty plugin |

---

## Template (copiar para novas entradas)

```markdown
## YYYY-MM-DD — Título curto

| Evento | Artefato | Notas |
|--------|----------|-------|
| **Accepted** | ADR-NNN | Resumo uma linha |
| **Superseded** | ADR-NNN | Substituído por ADR-MMM |
| **Approved** | RFC-NNN | |
| **Completed** | R{N}-F{M} | Versão semver |
```

---

## Referências

- `docs/ArchitectureDecisionIndex.md`
- `docs/decisions/ADR-Lifecycle.md`
- `docs/reviews/R2-ARB-FinalVerdict.md`
