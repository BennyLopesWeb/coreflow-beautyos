# R2-F1b — Gate Review

**Documento:** `docs/reviews/R2-F1b-GateReview.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Sprint:** R2-F1b · **Versão código:** `1.19.1-r2-f1b`  
**Veredito:** ✅ **ACCEPTED (tech)**

---

## Contexto

Revisão formal pós-implementação antes de iniciar **R2-F2**. Complementa DoD §15 de [R2-F1b.md](../sprints/R2-F1b.md) e fecha gates deliberadamente bloqueados em R2-F1.

| Métrica | Valor |
|---------|-------|
| Testes CI | **285 passed**, 6 skipped |
| Incremento vs R2-F1 | +6 testes (`test_r2_f1b_idempotency.py`) |
| Baseline anterior | 279 passed (R2-F1) |

---

## Validated

| # | Item | ADR / artefato | Evidência |
|---|------|----------------|-----------|
| V1 | TX flow idempotency → handler → save → commit | ADR-025 | `CreateBookingHandler.execute()` |
| V2 | `correlation_id` HTTP → outbox | ADR-027 | `DomainEvent.correlation_id`, test `test_correlation_id_in_outbox_on_create` |
| V3 | Idempotency-Key obrigatório + dedupe | ADR-031 | Tabela `idempotency_keys`, migration `cf012` |
| V4 | P12 retry semantics (201 → 200 → 409) | [R2-ParityMatrix](../architecture/R2-ParityMatrix.md) | `test_p12_idempotent_retry_same_key` |
| V5 | Request fingerprint `(key, payload_hash)` | ADR-031 | `compute_request_hash`, `test_idempotency_key_reused_different_body_409` |
| V6 | Rollback não persiste key | ADR-025 | `test_idempotency_not_saved_on_projection_failure` |
| V7 | Contrato API — sem header → 400 | ADR-031 | `test_create_without_idempotency_key_returns_400` |
| V8 | Fixture `booking_headers` — zero falso positivo | Governança testes | `conftest.py` + testes POST atualizados |
| V9 | Alias `reservation.created` + correlation | ADR-027 | Flag ON path inalterado + correlation |
| V10 | Métricas idempotency + correlation | Sprint §13 | `ArchitectureMetricsStore` |

---

## Known limitation (Technical Debt)

| ID | Descrição | Severidade | Owner |
|----|-----------|------------|-------|
| **TD-R2-F1b-001** | `OutboxService.record_and_publish()` faz `commit()` interno em modo `sync` — idempotency save ocorre em TX separada | 🟡 Média | R2-F2 |

### Situação atual vs ideal

```
Atual (2 TX lógicas):
  TX-A: Booking + Outbox + Projection  → commit (outbox)
  TX-B: IdempotencyKey                 → commit (handler)

Ideal (ADR-025):
  TX única: Booking + Outbox + Idempotency → COMMIT
```

**Mitigação vigente:** rollback testado; key não persiste em falha de projeção; comportamento externo correto (P12 PASS).

**Resolução planejada:** `OutboxService.defer_commit=True` — escopo **R2-F2** §3 item 1.

---

## Riscos residuais pós-gate

| Área | Estado |
|------|--------|
| Core SoT | ✅ |
| Dual-write create | ✅ |
| Feature flag create | ✅ |
| Schema migration | ✅ |
| Idempotency create | ✅ |
| Retry P12 | ✅ |
| Correlation tracing | ✅ |
| Outbox atomicity | 🟡 TD-R2-F1b-001 |
| Approve / reject domain | 🔒 R2-F2 |
| Optimistic locking | 🔒 R2-F2 |
| Staging F1 48h | 🟡 operacional — [checklist](../checklists/R2-F1-StagingValidation.md) |

---

## Gate para R2-F2

| # | Critério | Status |
|---|----------|--------|
| G1 | R2-F1b DoD §15 completo | ✅ |
| G2 | Gate Review ACCEPTED | ✅ |
| G3 | Sprint doc R2-F2 publicado | ☐ → [R2-F2.md](../sprints/R2-F2.md) |
| G4 | TD-R2-F1b-001 registrado em R2-F2 escopo | ✅ |
| G5 | Baseline ≥285 tests CI | ✅ |

**Autorização:** implementação R2-F2 em dev local imediata; produção após DoR F2 §5.

---

## Aprovações

| Papel | Status | Data |
|-------|--------|------|
| Platform / ARB (tech review) | ✅ ACCEPTED (tech) | 2026-07-09 |
| Staging validation F1 | ☐ Pendente | — |
| Architecture Board G4 | ☐ Pendente | — |

---

## Referências

- [R2-F1b Sprint](../sprints/R2-F1b.md)
- [R2-F2 Sprint](../sprints/R2-F2.md)
- ADR-025, ADR-027, ADR-031
- [ArchitectureDecisionLog.md](../ArchitectureDecisionLog.md)
