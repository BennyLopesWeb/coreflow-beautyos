# CoreFlow — Digital Operations Center (DOC)

**Documento:** `docs/DigitalOperationsCenter.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Estratégico — centro de comando executivo da plataforma  
**Audiência:** Platform ops, super admin, CTO office

---

## Visão

O **Digital Operations Center** é o painel unificado de saúde e operação do CoreFlow — consolidando observabilidade técnica, métricas de negócio da plataforma, marketplace e IA em **single pane of glass**.

Evolução natural de `GET /v1/platform/health` ✅ → UI executiva completa.

```mermaid
flowchart TB
    subgraph DOC["Digital Operations Center"]
        HEALTH[Platform Health]
        PLG[Plugins]
        EVT[Events]
        ERR[Errors]
        AI[AI Ops]
        REV[Revenue]
        TEN[Tenants]
        INT[Integrations]
        KPI[KPIs]
        OBS[Observability]
        MKT[Marketplace]
        USE[Usage]
    end

    subgraph Sources
        PH[/v1/platform/* ✅]
        GRAF[Grafana]
        BI[Platform Billing]
        FF[Feature Flags]
    end

    Sources --> DOC
```

---

## Módulos do painel

### 1. Health

- API uptime, error rate
- Core vs legacy HTTP %
- Readiness score average
- Constitution violations count
- Active incidents

*Source:* `/v1/platform/health` ✅

### 2. Plugins

- Plugins loaded vs registered
- Active tenants per plugin
- Hook error rates
- Manifest version drift

### 3. Eventos

- Events published/consumed rate
- Outbox lag
- Kafka consumer lag
- DLQ depth ✅
- Top event types

### 4. Erros

- 5xx by endpoint
- Failed workflows
- Integration errors
- Certification failures

*Source:* Alertmanager ✅, Loki 🔜

### 5. IA

- Token usage / cost today
- Agent invocations
- Provider latency
- Budget alerts
- Top agents by volume

### 6. Receita

- MRR / ARR platform
- Marketplace GMV
- Plan distribution
- Churn risk tenants

*Source:* `PlatformBilling.md` R5+

### 7. Tenants

- Active tenants count
- New signups / week
- Suspended accounts
- Top tenants by API volume

### 8. Integrações

- Connectors active
- Success rate per connector
- OAuth token expiring

### 9. KPIs plataforma

| KPI | Target |
|-----|--------|
| API availability | 99.9% |
| Legacy % | ↓ monthly |
| Test count | ↑ per release |
| Marketplace assets | ↑ |
| Partner NPS | >50 |

### 10. Observabilidade

- Link Grafana dashboards
- Trace search by correlation_id
- Feature flag state matrix

### 11. Marketplace

- Installs / day
- Top assets
- Publisher leaderboard
- Certification queue

### 12. Uso

- API requests total
- Storage consumed
- SMS/WhatsApp sent
- AI tokens

---

## API aggregation

```
GET /v1/platform/operations/summary  🔜
GET /v1/platform/health              ✅
GET /v1/platform/architecture-metrics ✅
GET /v1/platform/readiness-score     ✅
```

Future: BFF for DOC UI with role `platform_ops`.

---

## Alertas integrados

DOC displays active Alertmanager alerts + runbook links.

---

## Roadmap

| Release | Entrega |
|---------|---------|
| R2 | Extend health API with plugin metrics |
| R3 | `/operations/summary` JSON |
| R4 | Admin UI MVP (internal) |
| R5 | Revenue + marketplace panels |
| R6 | Partner read-only DOC slice |

---

## Referências

- `docs/ObservabilityPlatform.md`
- `docs/ArchitectureMetrics.md`
- `docs/CapabilityMaturityDashboard.md`
- `docs/PlatformBilling.md`
- R1-F2 platform endpoints
