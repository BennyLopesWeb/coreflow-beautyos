# R2-F1 — Staging Validation Checklist

**Documento:** `docs/checklists/R2-F1-StagingValidation.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Propósito:** Fechar pendências operacionais §18 de [R2-F1.md](../sprints/R2-F1.md) antes de canary / R2-F1b  
**Owner:** Platform Team  
**Baseline:** `1.19.0-r2-f1` · 279 tests CI ✅

---

## Pré-requisitos

| # | Item | ☐ |
|---|------|---|
| 1 | Deploy `1.19.0-r2-f1` em staging | |
| 2 | Migration `cf011` aplicada (`sync_status`, `version` em `core_bookings`) | |
| 3 | Alembic upgrade ou `migrate_schema` executado no host staging | |
| 4 | Baseline CI verde (279 passed) | ✅ |
| 5 | Responsável operacional designado | |

---

## 1. Configuração inicial

### 1.1 Variáveis de ambiente

```bash
# Path legado (baseline — deve funcionar antes de ligar core)
export FEATURE_BOOKING_CORE_ENABLED=false
export APP_VERSION=1.19.0-r2-f1
export APP_ENV=staging
```

| Check | Esperado | ☐ |
|-------|----------|---|
| `GET /v1/platform/health` | 200, version `1.19.0-r2-f1` | |
| `GET /v1/platform/flags` | `booking.core.enabled` = `false` | |

### 1.2 Canary tenant

Documentar aqui após execução:

| Campo | Valor |
|-------|-------|
| **company_id** | _preencher_ |
| **slug** | _preencher_ |
| **Responsável** | _preencher_ |
| **Data ativação** | _preencher_ |

---

## 2. Validação flag OFF (regressão F0.5)

**Objetivo:** confirmar zero regressão antes de ligar core path.

### 2.1 Create básico (P01 legacy)

```bash
curl -s -X POST "$STAGING_URL/v1/bookings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "customer_id": <ID>,
    "catalog_id": <ID>,
    "offering_id": <ID>,
    "scheduled_at": "<ISO8601 slot disponível>"
  }'
```

| Check | Esperado | ☐ |
|-------|----------|---|
| HTTP status | `201` | |
| `legacy_agendamento_id` | não nulo | |
| `status` | `pending_payment` | |
| Outbox | `booking.created` presente | |
| Métrica | `coreflow.booking.create.legacy_path.total` incrementa | |

### 2.2 Slot indisponível (P02 legacy)

| Check | Esperado | ☐ |
|-------|----------|---|
| HTTP status | `409` | |
| DB | nenhuma linha órfã em `core_bookings` / `agendamentos` | |

### 2.3 Double booking (P09 legacy)

| Check | Esperado | ☐ |
|-------|----------|---|
| 1º POST | `201` | |
| 2º POST mesmo slot | `409` | |
| DB | exatamente 1 agendamento | |

**Resultado seção 2:** ☐ PASS · ☐ FAIL — _notas:_

---

## 3. Ativação flag ON (canary)

```bash
export FEATURE_BOOKING_CORE_ENABLED=true
# Reiniciar app / reload config conforme deploy staging
```

| Check | Esperado | ☐ |
|-------|----------|---|
| `GET /v1/platform/flags` | `booking.core.enabled` = `true` | |
| Canary tenant isolado | apenas tenant documentado §1.2 | |

---

## 4. Validação flag ON (core path)

Repetir P01, P02, P09 com flag ON no canary tenant.

### 4.1 Create básico (P01 core)

| Check | Esperado | ☐ |
|-------|----------|---|
| HTTP status | `201` | |
| `core_bookings.sync_status` | `synced` | |
| `core_bookings.legacy_agendamento_id` | não nulo | |
| Outbox | `booking.created` **e** `reservation.created` (alias) | |
| Alias payload | `canonical_type: booking.created`, `deprecated_alias: true` | |
| Métrica | `coreflow.booking.create.core_path.total` incrementa | |

### 4.2 Slot indisponível (P02 core)

| Check | Esperado | ☐ |
|-------|----------|---|
| HTTP status | `409` | |
| TX | zero row em `core_bookings` para request falho | |

### 4.3 Double booking (P09 core)

| Check | Esperado | ☐ |
|-------|----------|---|
| 2º POST | `409` | |
| DB | 1 row core + 1 agendamento legado | |

**Resultado seção 4:** ☐ PASS · ☐ FAIL — _notas:_

---

## 5. Observabilidade (48h — gate G2/G4)

Período de observação: de _data/hora_ até _data/hora_ (mín. 48h).

| Métrica / query | Threshold | ☐ |
|-----------------|-----------|---|
| `coreflow.booking.projection.failures.total` | = 0 | |
| `coreflow.booking.create.core_path.total` | > 0 (canary traffic) | |
| `SELECT count(*) FROM core_bookings WHERE sync_status='drift'` | = 0 | |
| `SELECT count(*) FROM core_bookings WHERE sync_status='pending'` | = 0 após commits | |
| Logs ERROR em `LegacyBookingAdapter.project_create` | 0 | |

**Resultado 48h:** ☐ PASS · ☐ FAIL — _notas:_

---

## 6. Rollback rehearsal (DoD §8)

Simular falha operacional **sem** deploy revert.

### 6.1 Flag OFF imediato

```bash
export FEATURE_BOOKING_CORE_ENABLED=false
# Reiniciar / reload
```

| Check | Esperado | ☐ |
|-------|----------|---|
| Tempo até flag OFF efetivo | < 5 min | |
| POST create pós-rollback | path ACL F0.5 (`201`) | |
| P01/P02/P09 | PASS flag OFF | |

### 6.2 Orphans aceitáveis

| Check | Esperado | ☐ |
|-------|----------|---|
| Rows `core_bookings` criadas durante canary | permanecem (ADR-024) | |
| Creates pós-rollback | só legado path | |

**Resultado rollback:** ☐ PASS · ☐ FAIL — _notas:_

---

## 7. Sign-off

| Gate R2-F1 §16 | Critério | Status |
|----------------|----------|--------|
| G2 | Dual-write estável 48h, zero projection rollback | ☐ |
| G3 | Zero `sync_status=drift` canary | ☐ |
| G4 | Telemetria §13 validada staging | ☐ |
| G5 | FF-EVT-005 WARN | ☐ |
| G6 | FF-EVT-007 WARN (alias) | ☐ |
| DoR D5 | G4 Architecture Board sign-off | ☐ |
| DoR D6 | Canary `company_id` documentado §1.2 | ☐ |

### Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Platform Lead | | | |
| ARB delegate | | | |

---

## 8. Pós-validação

Após todos ✅:

1. Atualizar [R2-F1.md §18](../sprints/R2-F1.md) — staging ✅  
2. Registrar em [ArchitectureDecisionLog.md](../ArchitectureDecisionLog.md)  
3. Liberar **implementação** R2-F1b conforme [R2-F1b.md](../sprints/R2-F1b.md) DoR §5  

---

## Referências

- [R2-F1 Sprint](../sprints/R2-F1.md) §14 Rollback · §16 Gates F1b · §18 Operational Validation  
- [R2-ParityMatrix](../architecture/R2-ParityMatrix.md) P01, P02, P09  
- ADR-024, ADR-025, ADR-027, ADR-032
