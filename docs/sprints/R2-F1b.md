# Release 2 — Sprint R2-F1b

**Documento operacional único desta sprint** — referência para desenvolvedores e IA. ADRs detalhados são normativos; este doc consolida o necessário para executar sem navegar entre múltiplos artefatos.

---

## 1. Identificação da Sprint

| Campo | Valor |
|-------|-------|
| **Sprint** | R2-F1b |
| **Versão** | `1.19.1-r2-f1b` |
| **Status** | ✅ Accepted (tech) |
| **Release** | R2 — Core Domain Consolidation |
| **Fase anterior** | R2-F1 ✅ Accepted (tech) (`1.19.0-r2-f1`) |
| **Próxima fase** | R2-F2 — Approve / Reject — [R2-F2.md](./R2-F2.md) |
| **Owner** | Platform Team — [DomainOwnership.md](../DomainOwnership.md) |
| **Objetivo estratégico** | Tornar **create booking** seguro para retries HTTP e rastreável ponta-a-ponta via **Idempotency-Key** e **correlation_id**. |

---

## 2. Objetivo

Complementar R2-F1 com garantias de **idempotência obrigatória** em `POST /v1/bookings` e **correlation_id** no envelope de eventos, conforme ADR-031 e ADR-027 (mínimo RFC-009).

**Não altera** regras de domínio create (INV-B1–B3) nem dual-write TX — apenas envolve o fluxo existente com dedupe e observabilidade.

**Resultado mensurável:** P12 PASS; P01 estendido com Idempotency-Key; `correlation_id` presente em outbox para eventos HTTP-originated; FF-API-005 WARN → ERROR ready.

---

## 3. Escopo IN

| # | Entrega | Detalhe |
|---|---------|---------|
| 1 | Header `Idempotency-Key` obrigatório | `POST /v1/bookings` — ADR-031 |
| 2 | Tabela `idempotency_keys` | `(key, company_id, endpoint, request_hash, response_body, booking_id, expires_at)` |
| 3 | `IdempotencyStore` port + adapter | Check antes do handler; save na mesma TX ADR-025 |
| 4 | Integração `CreateBookingHandler` | Ordem TX: idempotency check → domain → projection → outbox → idempotency save → COMMIT |
| 5 | `correlation_id` no envelope | `DomainEvent` + outbox payload — ADR-027 |
| 6 | Propagação HTTP → handler → eventos | Header `X-Correlation-Id` ou gerar UUID se ausente |
| 7 | Problem Details | `400 idempotency_key_required`, `409 idempotency_key_reused` |
| 8 | OpenAPI `/v1/bookings` | Documentar header + respostas idempotentes |
| 9 | Paridade **P12** | Retry mesmo key → mesmo `booking_id`; body diferente → 409 |
| 10 | Paridade **P01** estendido | Create com Idempotency-Key flag ON e OFF |
| 11 | Telemetria idempotency | hits, misses, conflicts |
| 12 | Testes unit + integration | §11 |

---

## 4. Escopo OUT

**Proibido nesta sprint** — scope creep → parar → ARB.

| Item | Fase correta |
|------|--------------|
| `approve()` / `reject()` domain path | R2-F2 |
| Idempotency obrigatória approve/reject/cancel | R2-F2 (recommended ADR-031) |
| Optimistic lock / ETag / `If-Match` | R2-F2 |
| `version` increment em transições | R2-F2 |
| Resource Engine | R2-F3 |
| Reconciliation job | R2-F5 |
| RFC-009 envelope completo (Avro, schema registry) | R3 |
| Remover alias `reservation.created` | R3-F2 |
| Alterar dual-write / aggregate create | Proibido — já Accepted F1 |

---

## 5. Pré-requisitos (DoR)

Gate **obrigatório** antes do primeiro commit. Ver [DefinitionOfReady-Architecture.md](../decisions/DefinitionOfReady-Architecture.md).

### Gates herdados de R2-F1 §16

| # | Critério | Status |
|---|----------|--------|
| G1 | P01, P02, P09 PASS (CI) | ✅ |
| G2 | Dual-write estável staging 48h | ☐ — [checklist](../checklists/R2-F1-StagingValidation.md) §5 |
| G3 | Zero `sync_status=drift` canary | ☐ |
| G4 | Telemetria §13 staging | ☐ |
| G5 | FF-EVT-005 WARN | ☐ staging |
| G6 | FF-EVT-007 WARN (alias) | ☐ staging |
| G7 | DoD F1 completo | ✅ |
| G8 | Sprint doc R2-F1b | ✅ |

### DoR específico F1b

| # | Critério | Status |
|---|----------|--------|
| D1 | R2-F1 Accepted (tech) | ✅ |
| D2 | ADR-031, ADR-025, ADR-027 Accepted | ✅ |
| D3 | Staging validation §18 F1 executada | ☐ |
| D4 | Canary `company_id` documentado | ☐ |
| D5 | G4 Architecture Board sign-off | ☐ |
| D6 | Este sprint doc aprovado | ☐ |
| D7 | Baseline testes ≥279 passed | ✅ |

**Regra:** DoR incompleto (G2–G6 staging + D3–D5) → **não iniciar implementação em produção**; desenvolvimento local permitido com flag OFF default.

Checklist operacional: [R2-F1-StagingValidation.md](../checklists/R2-F1-StagingValidation.md).

---

## 6. ADRs obrigatórios (resumo operacional)

| ADR | Aplicação nesta sprint |
|-----|------------------------|
| [ADR-031](../adr/ADR-031-IdempotencyConcurrency.md) | Idempotency-Key mandatory create; dedupe table; TTL 24h |
| [ADR-025](../adr/ADR-025-TransactionBoundaries.md) | IdempotencyStore dentro da TX core path |
| [ADR-027](../adr/ADR-027-ReservationToBookingMigration.md) | `correlation_id` no envelope; alias inalterado |
| [ADR-024](../adr/ADR-024-DualWriteStrategy.md) | Idempotency não bypassa dual-write |

**Regra de conflito:** ADR vence sprint doc.

---

## 7. Fluxo aprovado

### POST /v1/bookings — com Idempotency-Key (F1b)

```
HTTP POST /v1/bookings
Headers: Idempotency-Key, X-Correlation-Id (opcional)
    ↓
API Layer — validar header obrigatório (400 se ausente)
    ↓
IdempotencyStore.check(key, company_id, endpoint, body_hash)
    ├─ HIT same body  → return cached response (200/201 conforme ADR-031)
    ├─ HIT diff body  → 409 idempotency_key_reused
    └─ MISS           → continuar
    ↓
correlation_id = header ou uuid4()
    ↓
CreateBookingHandler (flag ON ou OFF — inalterado F1)
    ↓
BEGIN TRANSACTION
    ↓
[core path F1 ou ACL path F0.5]
    ↓
Outbox events com correlation_id
    ↓
IdempotencyStore.save(key, booking_id, response_snapshot)
    ↓
COMMIT
    ↓
Return response
```

**Retry seguro:** cliente reenvia **mesmo** `Idempotency-Key` + **mesmo** body → resposta cacheada, zero duplicate booking.

**Flag OFF:** idempotency aplica-se igualmente — protege ACL path contra retries.

---

## 8. Arquivos previstos

| Arquivo | Ação | Notas |
|---------|------|-------|
| `shared/idempotency/idempotency_store.py` | **Novo** | Port + SQLAlchemy adapter |
| `shared/idempotency/models.py` | **Novo** | ORM `IdempotencyKey` |
| `shared/events/domain_event.py` | **Alterar** | Campo `correlation_id` |
| `shared/events/outbox.py` | **Alterar** | Persistir correlation_id |
| `modules/booking/domain/events.py` | **Alterar** | Passar correlation_id nas factories |
| `modules/booking/application/commands/create_booking.py` | **Alterar** | Receber correlation_id; TX idempotency save |
| `routers/v1_bookings.py` | **Alterar** | Headers; Problem Details; OpenAPI |
| `core/architecture_metrics.py` | **Alterar** | Métricas idempotency |
| `core/exceptions.py` | **Alterar** | `IdempotencyKeyRequired`, `IdempotencyKeyReused` |
| `alembic/versions/cf012_r2_f1b_idempotency.py` | **Novo** | Tabela `idempotency_keys` |
| `app/db/migrate_schema.py` | **Alterar** | SQLite incremental se necessário |
| `tests/test_core/test_r2_f1b_idempotency.py` | **Novo** | P12 + unit |
| `tests/test_core/test_r2_f1_booking_create.py` | **Alterar** | Headers nos testes existentes |
| `docs/sprints/R2-F1b.md` | **Alterar** | DoD ao concluir |

**Não alterar:** `approve_booking.py`, `reject_booking.py`, aggregate `Booking.create()` invariantes.

---

## 9. Feature Flags

| Chave pública | Env var | Estado inicial | Pós-sprint | Rollback |
|---------------|---------|----------------|------------|----------|
| `booking.core.enabled` | `FEATURE_BOOKING_CORE_ENABLED` | `false` | inalterado | `false` |

F1b **não introduz** flag nova. Idempotency aplica-se com flag ON e OFF.

### Rollback operacional

```bash
# Idempotency é backward-compatible — rollback = revert PR
git revert <commit-r2-f1b>
export APP_VERSION=1.19.0-r2-f1

# Tabela idempotency_keys pode permanecer (orphan rows OK)
# Clientes sem header passam a receber 400 — coordenar release mobile/API
```

---

## 10. Eventos

| Evento | Alteração F1b | Obrigatório |
|--------|---------------|-------------|
| `booking.created` | + `correlation_id` no envelope | ✅ |
| `reservation.created` (alias) | + `correlation_id`; mesmo valor do primário | ✅ flag ON |
| Demais eventos | Sem alteração nesta sprint | — |

### Envelope mínimo (ADR-027 + F1b)

```json
{
  "event_type": "booking.created",
  "event_id": "uuid",
  "event_version": "v1",
  "aggregate_id": "123",
  "aggregate_type": "Booking",
  "company_id": 1,
  "correlation_id": "uuid",
  "occurred_at": "2026-07-09T12:00:00Z",
  "payload": { }
}
```

---

## 11. Testes obrigatórios

### Unit

| Área | Casos |
|------|-------|
| `IdempotencyStore` | save, hit same body, hit diff body, TTL expiry |
| `DomainEvent` | correlation_id propagation |
| Request hash | normalização body JSON estável |

### Integration

| Área | Casos |
|------|-------|
| Create sem header | `400 idempotency_key_required` |
| Create + retry same key | P12 — single row, cached response |
| Create + same key diff body | `409 idempotency_key_reused` |
| Flag ON + OFF | idempotency funciona em ambos paths |
| TX rollback | idempotency key **não** salvo se projection falhar |

### Paridade

| ID | Cenário | Gate merge |
|----|---------|------------|
| P01 | Create com Idempotency-Key | ☐ |
| P12 | Retry idempotent create | ☐ |

Arquivo: `tests/test_core/test_r2_f1b_idempotency.py`

---

## 12. Fitness Functions

| ID | Regra | Severidade F1b | Ação |
|----|-------|----------------|------|
| FF-API-005 | `Idempotency-Key` documentado OpenAPI POST bookings | WARN → **ERROR** | Block merge |
| FF-EVT-006 | `correlation_id` when HTTP-originated | WARN | Merge OK |
| FF-EVT-001 | Events in catalog | ERROR | Block |
| FF-TST-003 | Paridade P12 | ERROR | Block |

Referência: [ArchitectureFitnessFunctions.md](../ArchitectureFitnessFunctions.md).

---

## 13. Métricas (observabilidade)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `coreflow.idempotency.hits.total` | Counter | Cache hit — retry seguro |
| `coreflow.idempotency.misses.total` | Counter | First request processed |
| `coreflow.idempotency.conflicts.total` | Counter | Same key, different body |
| `coreflow.idempotency.missing_key.total` | Counter | 400 rejected |
| `coreflow.events.correlation_id.present` | Counter | Eventos com correlation_id |

---

## 14. Rollback

### Gatilhos

| Gatilho | Ação |
|---------|------|
| P12 FAIL | Revert PR |
| Duplicate bookings despite key | Flag OFF + hotfix |
| 400 spike (clientes sem header) | Feature toggle soft-require* ou revert |

\*Soft-require **fora de escopo F1b** — ADR-031 exige mandatory; coordenar release clientes.

### Procedimento

1. `git revert <merge-commit-r2-f1b>`
2. `APP_VERSION=1.19.0-r2-f1`
3. Validar P01/P02/P09 sem header requirement (F1 baseline)
4. Registrar em `ArchitectureDecisionLog.md` se P1

---

## 15. Critério de Conclusão (DoD)

| # | Critério | ☐ |
|---|----------|---|
| 1 | Código mergeado — escopo §3 only | ✅ |
| 2 | `pytest` verde — ≥279 + novos F1b | ✅ (285 passed) |
| 3 | P01 (com key) + P12 PASS flag ON e OFF | ✅ |
| 4 | `correlation_id` em outbox create events | ✅ |
| 5 | FF-API-005 ERROR pass | ✅ (OpenAPI header) |
| 6 | FF-EVT-006 WARN pass | ✅ |
| 7 | OpenAPI atualizado | ✅ (Header documentado) |
| 8 | Métricas §13 | ✅ |
| 9 | Sprint doc + Decision Log | ✅ |
| 10 | `APP_VERSION=1.19.1-r2-f1b` | ✅ |

---

## 16. Critério de GO para R2-F2

| # | Gate |
|---|------|
| G1 | P12 = **PASS** (CI) |
| G2 | Idempotency estável staging 48h |
| G3 | Zero duplicate booking reports |
| G4 | FF-API-005 ERROR pass |
| G5 | DoD F1b completo §15 |
| G6 | Sprint doc R2-F2 criado |

**F2 escopo exclusivo:** approve/reject domain, PaymentQueryPort, optimistic lock, P03–P05, P08.

---

## 17. Lições aprendidas

_Preencher ao concluir._

| Data | Lição | Ação follow-up |
|------|-------|----------------|
| 2026-07-09 | Idempotency save após outbox sync-mode (commit interno) — TX ideal ADR-025 requer `defer_commit` no OutboxService | Avaliar refactor Outbox em R2-F2 |
| 2026-07-09 | Fixture `booking_headers` centraliza header em todos os testes POST bookings | Manter em conftest para novos testes |

---

## Referências rápidas

| Documento | Path |
|-----------|------|
| **Gate Review** | [R2-F1b-GateReview.md](../reviews/R2-F1b-GateReview.md) ✅ ACCEPTED |
| Execution Plan R2 v4 | [R2-ExecutionPlan.md](../R2-ExecutionPlan.md) |
| Sprint anterior | [R2-F1.md](./R2-F1.md) |
| Staging checklist F1 | [R2-F1-StagingValidation.md](../checklists/R2-F1-StagingValidation.md) |
| Paridade | [R2-ParityMatrix.md](../architecture/R2-ParityMatrix.md) |
| Template | [templates/SprintTemplate.md](../templates/SprintTemplate.md) |

---

**Última atualização:** 2026-07-09 · **Status:** ✅ Accepted (tech) · `1.19.1-r2-f1b` · 285 tests
