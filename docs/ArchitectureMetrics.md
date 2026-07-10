# CoreFlow — Architecture Metrics

**Documento:** `docs/ArchitectureMetrics.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Normativo — KPIs arquiteturais contínuos  
**Implementação runtime:** R1-F2 (`ArchitectureMetricsStore`, `/v1/platform/architecture-metrics`)

---

## Propósito

Medir **qualidade arquitetural** além de métricas HTTP tradicionais. Estes indicadores orientam releases, priorizam Strangler Fig e detectam degradação antes que vire dívida crítica.

---

## Categorias de indicadores

### 1. Acoplamento

| Métrica | Descrição | Fonte | Alvo R2 | Alvo R7 |
|---------|-----------|-------|---------|---------|
| **Couplings count** | Acoplamentos Core↔Legado identificados | `identified_couplings()` | ≤3 | 0 |
| **ACL coverage %** | Contextos com ACL vs delegação direta | Audit estática | 80% | 100% |
| **Cross-context imports** | Imports diretos entre modules domain | Linter custom / grep CI | ↓ | 0 |
| **Circular dependencies** | Ciclos entre pacotes Python | `import-linter` (🔜 CI) | 0 | 0 |
| **Plugin→Core violations** | Plugin importa models legado | CI scan | 0 | 0 |

**Alerta:** Coupling count aumenta sprint-over-sprint → bloquear merge até ADR.

### 2. Coesão

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **Modules w/ clear layers** | Módulos com domain/application/infrastructure | Audit | 6/18 R2, 18/18 R7 |
| **SRP violations** | Services >500 LOC ou multi-responsibility | Static analysis | ↓ |
| **Shared kernel changes** | PRs tocando `shared/` por sprint | Git | ≤2 (estabilizar) |

### 3. Cobertura de testes

| Métrica | Descrição | Fonte | Alvo R2 | Alvo R7 |
|---------|-----------|-------|---------|---------|
| **Total test files** | Arquivos `test_*.py` | pytest collect | 280+ | 500+ |
| **Coverage by module** | Test files por área | `test_coverage_by_module()` | all "covered" | all "covered" |
| **Parity tests** | Testes legado vs v1 | `test_cf*.py` | booking full | all writes |
| **Test pass rate** | CI green | GitHub Actions | 100% | 100% |

**Nota:** Coverage % linha (pytest-cov) 🔜 CI — meta 70% core modules R3.

### 4. Uso do Core vs Legado

| Métrica | Descrição | Fonte | Alvo R2 | Alvo R7 |
|---------|-----------|-------|---------|---------|
| **Legacy HTTP %** | Requests legacy+beautyos / total | `ArchitectureMetricsStore` | <30% | <1% |
| **Core HTTP %** | Requests layer=core / total | idem | ≥70% | ≥99% |
| **ACL invocations** | Chamadas adapter ACL | idem | ↑ tracking | ↓ (legado zero) |
| **Legacy writes blocked** | 403 enforcement | Prometheus | 0 (warn only) | 100% blocked |

Endpoint: `GET /v1/platform/health` → `legacy.percentage`

### 5. Uso dos Plugins

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **Plugin requests** | Acessos por plugin_id | `ArchitectureMetricsStore.plugins` | tracking |
| **Active plugins** | Plugins status=active | Plugin registry | 1 R2, 5+ R7 |
| **Hook executions** | Handlers plugin invocados | Event metrics (🔜) | tracking |

### 6. Eventos

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **Events published total** | Publicações event bus | Architecture metrics | ↑ saudável |
| **Events consumed total** | Handlers executados | idem | ≈ published |
| **Outbox lag** | Pending outbox rows | DB query / Prometheus | <100 |
| **DLQ depth** | Mensagens DLQ | Kafka metrics | 0 steady-state |
| **Event catalog implemented %** | implemented / total | event catalog API | 50% R2, 90% R7 |

### 7. Latência

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **Avg duration by layer** | Segundos por layer | Architecture metrics | core ≤ legacy |
| **P95 HTTP** | histogram_quantile | Prometheus | <500ms API |
| **P95 booking create** | Endpoint specific | Grafana | <800ms |

Dashboard: `coreflow-api-layers` (Grafana)

### 8. Complexidade

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **Readiness score average** | Maturidade arquitetural | `/v1/platform/readiness-score` | 45 R2, 75 R7 |
| **ArchitectureAssessment score** | Auditoria periódica | Manual quarterly | 6.5 R2, 9.0 R7 |
| **LOC legacy services** | Linhas `app/services/` | cloc CI | ↓ 20%/release |
| **API surface count** | Rotas ativas por layer | legacy_route_map | ↓ legacy |

### 9. Build & Deploy

| Métrica | Descrição | Fonte | Alvo |
|---------|-----------|-------|------|
| **CI duration** | GitHub Actions total | CI metrics | <10 min |
| **Test suite duration** | pytest wall time | CI | <3 min |
| **Deploy frequency** | Deploys/semana staging | Ops | ≥2 |
| **MTTR** | Mean time to recovery | Incident log | <30 min |
| **Rollback count** | Rollbacks/release | Sprint docs | ≤1 |

---

## Core Readiness Score (dimensões)

Painel em `/v1/platform/readiness-score`:

| Dimensão | Base R1-F2 | Alvo R2 | Alvo R7 |
|----------|------------|---------|---------|
| Hexagonal | 35% | 55% | 90% |
| DDD | 40% | 60% | 85% |
| Plugin Architecture | 55% | 75% | 95% |
| Resource Engine | 15% | 60% | 90% |
| Scheduling Engine | 20% | 50% | 85% |
| AI Platform | 10% | 25% | 80% |
| Workflow Engine | 25% | 45% | 75% |
| Marketplace | 0% | 5% | 70% |
| API First | 45% | 70% | 95% |
| Event Driven | 55% | 70% | 90% |
| Observability | 50% | 65% | 90% |

Metodologia: base estática (Architecture Assessment) + boost runtime (ex.: `api_first` += core HTTP %).

---

## Dashboards

| Dashboard | UID | Audiência |
|-----------|-----|-----------|
| API Layers & Migration | `coreflow-api-layers` | Platform ops |
| Platform Health | `/v1/platform/health` JSON | Admin panel, audits |
| Architecture Metrics | `/v1/platform/architecture-metrics` | Architects |
| Readiness Score | `/v1/platform/readiness-score` | Product + architects |

Export: `POST /v1/platform/grafana/dashboard/layers/export`

---

## Cadência de revisão

| Frequência | Ação |
|------------|------|
| **Cada sprint** | Snapshot readiness + legacy % no sprint doc |
| **Cada release** | Re-run Architecture Assessment |
| **Quarterly** | Review couplings + circular deps + score targets |
| **Anual** | Atualizar metas R7 neste documento |

---

## Alertas recomendados (Alertmanager)

| Alerta | Condição | Severidade |
|--------|----------|------------|
| LegacyUsageHigh | legacy % > 50% por 7d | warning |
| DLQDepth | dlq messages > 10 | critical |
| APIErrorRate | 5xx rate > 1% | critical |
| OutboxLag | pending > 500 | warning |
| ReadinessDrop | average < previous release | warning |

---

## Integração CI (🔜 R2)

```yaml
# .github/workflows/architecture-metrics.yml (proposta)
- name: Architecture gate
  run: |
    pytest tests/test_core/test_r1_f2_platform_observability.py -o addopts=
    python scripts/architecture_gate.py --max-couplings 4 --min-tests 268
```

---

## Referências

- `backend/app/core/architecture_metrics.py`
- `backend/app/modules/platform/application/readiness_score_service.py`
- `docs/sprints/R1-F2.md`
- `docs/ArchitectureAssessment.md`
- Grafana: `infra/grafana/dashboards/coreflow-api-layers.json`
