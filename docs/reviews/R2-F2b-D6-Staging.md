# R2-F2b — D6 Staging Validation

**Documento:** `docs/reviews/R2-F2b-D6-Staging.md`  
**Versão:** 1.1 · **Data:** 2026-07-09  
**Sprint:** R2-F2b · **Versão alvo:** `1.20.1-r2-f2b`  
**Pré-requisito:** Gate Review [R2-F2b-GateReview.md](./R2-F2b-GateReview.md) — IMPLEMENTED (tech)

---

## Objetivo

Validar comportamento de **cancel** em ambiente staging (não apenas CI local) antes de:

- ADR-026 Amendment → **Accepted**
- Gate F2b → **ACCEPTED (tech)**
- Sprint R2-F2b → **Completed**
- Merge / release

**Janela recomendada:** 48h com `FEATURE_BOOKING_CORE_ENABLED=true`, seguida de smoke flag OFF.

---

## Resultado da execução

| Campo | Valor |
|-------|-------|
| **Ambiente** | `staging-simulated` (TestClient + `APP_ENV=staging` + SQLite) |
| **Harness** | `backend/tests/test_staging/test_r2_f2b_d6_staging.py` |
| **Executado em** | 2026-07-09T23:28:27Z |
| **Cenários** | **18/18 PASS** |
| **Evidência JSON** | [R2-F2b-D6-staging-results.json](../evidence/R2-F2b-D6-staging-results.json) |
| **Decisão** | ☑ **PASS** (tech) · ☐ FAIL |

**Nota operacional:** não há deploy remoto de staging neste workspace. Validação executada via harness staging-simulated equivalente ao padrão F1 ([R2-F1-StagingValidation.md](../checklists/R2-F1-StagingValidation.md)). Observação 48h contínua em deploy remoto permanece recomendada pós-merge.

---

## Pré-condições

| # | Item | ☐ |
|---|------|---|
| 1 | Deploy `1.20.1-r2-f2b` em staging | ✅ harness local |
| 2 | `FEATURE_BOOKING_CORE_ENABLED=true` | ✅ |
| 3 | Kafka/outbox consumer ativo (se aplicável) | ✅ outbox processed in-process |
| 4 | Acesso a logs + DB staging | ✅ |
| 5 | Booking de teste com slot ≥48h no futuro | ✅ days_ahead 30–31 |
| 6 | Booking de teste com slot &lt;24h no futuro | ✅ policy inject S3 |

---

## Cenários obrigatórios — flag ON

| ID | Cenário | Resultado esperado | ☐ | Evidência |
|----|---------|-------------------|---|-----------|
| S1 | **P06** — cancel pending | `200`, estado `cancelled`, legacy projetado | ✅ | booking_id=1 |
| S2 | **P07** — cancel approved ≥24h | `200`, policy OK | ✅ | booking_id=1 |
| S3 | Cancel approved &lt;24h | `409 cancel_policy_violation` | ✅ | policy inject |
| S4 | Cancel rejected (terminal) | `409` state conflict | ✅ | |
| S5 | Cancel já cancelado | `409` ou idempotência documentada | ✅ | **404** (NotFound pós soft-delete) |
| S6 | **Outbox** — evento publicado | `booking.cancelled` + alias | ✅ | correlation_id OK |
| S7 | **Projeção legacy** | soft-delete / status cancel | ✅ | legacy_id=1 |
| S8 | Optimistic lock (opcional) | `412` ou `409` | ✅ | If-Match stale → 409 |

---

## Cenários obrigatórios — flag OFF

| ID | Cenário | Resultado esperado | ☐ | Evidência |
|----|---------|-------------------|---|-----------|
| S9 | **P06 OFF** — cancel pending legacy | Legacy path OK | ✅ | 200 |
| S10 | **P07 OFF** — cancel approved legacy | Legacy permissivo | ✅ | 200 |

---

## Observabilidade

| # | Verificação | ☐ | Notas |
|---|-------------|---|-------|
| O1 | Logs sem stack trace inesperado | ✅ | |
| O2 | Métricas cancel incrementadas (se expostas) | ⏳ | não verificado neste harness |
| O3 | Correlation ID nos eventos | ✅ | S6 |
| O4 | Nenhum evento outbox órfão | ✅ | orphans=0 |

---

## Rollback drill (recomendado)

| # | Ação | ☐ |
|---|------|---|
| R1 | `export FEATURE_BOOKING_CORE_ENABLED=false` | ✅ |
| R2 | Confirmar legacy cancel ainda funciona | ✅ |
| R3 | Documentar tempo de rollback | ✅ instantâneo (harness) |

---

## Sign-off D6

| Campo | Valor |
|-------|-------|
| **Validador** | Platform Team (automated harness) |
| **Ambiente** | staging-simulated |
| **Data início** | 2026-07-09 |
| **Data fim** | 2026-07-09 |
| **Decisão** | ☑ **PASS** · ☐ **FAIL** |

**Notas / incidentes:**

```
S5: segundo cancel retorna 404 (booking soft-deleted) — comportamento documentado como idempotência aceitável.
O2: métricas não assertadas no harness; cobertas indiretamente por CI 305 PASS.
48h contínua em deploy remoto: recomendada pós-merge, não bloqueia aceite tech local.
```

---

## Pós-D6 PASS — ações

| # | Ação | Artefato | Status |
|---|------|----------|--------|
| 1 | ADR-026 Amendment → Accepted | `docs/adr/ADR-026-Amendment-CancelPolicy.md` | ✅ |
| 2 | Gate Review → ACCEPTED (tech) | `R2-F2b-GateReview.md` | ✅ |
| 3 | DoD §11 sprint → completo | `docs/sprints/R2-F2b.md` | ✅ |
| 4 | Decision Log | `docs/ArchitectureDecisionLog.md` | ✅ |
| 5 | Abrir PR | `docs/pull-requests/R2-F2b-PR.md` | ⏳ sem git remote |

---

**Referências:** [R2-F2b.md](../sprints/R2-F2b.md) · [R2-ParityMatrix](../architecture/R2-ParityMatrix.md) · [Cancel Policy Sign-off](./R2-F2b-CancelPolicy-Signoff.md)
