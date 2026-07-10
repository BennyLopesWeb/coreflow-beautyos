# CoreFlow — Product Capability Map

**Documento:** `docs/ProductCapabilityMap.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Estratégico — inventário de capacidades  
**Base:** Architecture Assessment + módulos existentes v1.17.0-r1-f2

---

## Legenda de classificação

| Classificação | Significado |
|---------------|-------------|
| **Core** | Capacidade universal — `app/modules/` ou `app/core/` |
| **Plugin** | Especialização vertical — `backend/plugins/{id}/` |
| **Future** | Planejado — documentado, não implementado |
| **Experimental** | Stub ou MVP — pode mudar ou ser removido |
| **Legacy** | Legado ativo — sunset via Strangler Fig |

---

## Mapa de capacidades

### Identity & Access

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| JWT Authentication | **Core** | ✅ Produção | `modules/identity/` |
| RBAC (owner/admin/staff) | **Core** | ✅ Produção | `CompanyRole` |
| Multi-tenant (company_id) | **Core** | ✅ Produção | `TenantContext` |
| OAuth / SSO | **Future** | 🔜 | Gap assessment |
| API Keys (integradores) | **Future** | 🔜 | Release 6 |
| Rate limiting | **Future** | 🔜 | Release 3 |

### Organization

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Company (tenant) | **Core** | ✅ Produção | `companies` |
| Location | **Core** | ⚠️ Parcial | `core_locations` |
| Business (holding) | **Future** | 🔜 | Meta model |
| Plugin config per tenant | **Core** | ✅ Produção | `/v1/plugins/config/by-company/{slug}` |
| White-label theming | **Plugin** + **Future** | ⚠️ Parcial | EAS whitelabel CF-17 |

### Catalog & Commerce

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Catalog / Offering | **Core** | ✅ v1 + legacy sync | `/v1/catalogs` |
| Service gallery layout | **Plugin** | ✅ | beauty `ui.catalog_layout` |
| Pricing rules advanced | **Future** | 🔜 | — |
| Marketplace listings | **Experimental** | Stub | `/v1/marketplace` |

### Booking & Scheduling

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Booking CRUD v1 | **Core** | ⚠️ Delega legado | `/v1/bookings` |
| Approve / Reject | **Core** | ⚠️ Delega legado | commands CQRS |
| Waitlist | **Core** | ✅ v1 + sync | `/v1/waitlist` |
| Scheduling engine | **Core** | ⚠️ Parcial | `scheduling_engine.py` |
| Resource Engine | **Core** | **Future** R2 | ADR-007 |
| Recurring bookings | **Future** | 🔜 | Release 3 |
| No-show handling | **Future** | 🔜 | Event `booking.no_show` |
| Operational queue | **Core** + **Plugin** | Legacy + feature flag | beauty `operational_queue` |
| ReservationService | **Legacy** | ✅ Sunset path | `app/services/` |

### CRM & Customer

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Customer CRUD v1 | **Core** | ✅ | `/v1/customers` |
| CRM follow-up AI | **Plugin** | ⚠️ Acoplado core | beauty `crm_followup` → migrar |
| Segmentation / campaigns | **Future** | 🔜 | Release 3 |
| Customer 360 view | **Future** | 🔜 | Analytics |

### Finance

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Payments / deposit | **Core** | ✅ v1 + legacy | `/v1/payments` |
| Orders | **Core** | ✅ | `/v1/orders` |
| Invoices | **Core** | ✅ | `/v1/invoices` |
| Finance ledger (legado) | **Legacy** | ✅ | `/financeiro/*` |
| Multi-currency | **Future** | 🔜 | Release 7 |
| Subscription billing (SaaS) | **Future** | 🔜 | Platform billing |

### Inventory & Assets

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Assets | **Core** | ✅ | `/v1/assets` |
| Inventory | **Core** | ✅ | `/v1/inventory` |
| Product catalog (retail) | **Future** | 🔜 | Plugin restaurant |

### Automation

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Workflow engine (YAML) | **Core** | ✅ | `modules/workflow/` |
| Event-driven triggers | **Core** | ✅ | Event catalog |
| Visual workflow editor | **Future** | 🔜 | Release 4 |
| WhatsApp automation | **Plugin/Future** | 🔜 | Action adapter |

### Notification

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Push (Expo) | **Core** | ✅ | `modules/push/` |
| Deep links | **Core** + **Plugin** | ✅ | manifest `deep_links` |
| Email / SMS | **Future** | 🔜 | Notification port |
| In-app inbox | **Future** | 🔜 | — |

### AI

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| LLM provider registry | **Core** | ⚠️ MVP | `llm_service.py` |
| Mock / OpenAI providers | **Core** | ✅ | `providers/` |
| Agent shell genérico | **Future** | 🔜 | Release 4 |
| BeautyAgent | **Plugin** | ⚠️ No core ainda | Migrar R2-R3 |
| RAG tenant-scoped | **Future** | 🔜 | Release 4 |
| MCP integration | **Future** | 🔜 | Vision 2030 |

### Analytics & Reporting

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Platform health metrics | **Core** | ✅ R1-F2 | `/v1/platform/health` |
| Architecture metrics | **Core** | ✅ R1-F2 | `/v1/platform/architecture-metrics` |
| Readiness score | **Core** | ✅ R1-F2 | `/v1/platform/readiness-score` |
| Business analytics | **Future** | 🔜 | Release 3 |
| Audit trail API | **Future** | 🔜 | Release 3 |

### Platform & Governance

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Feature flags | **Core** | ✅ | `feature_flags.py` |
| ACL (Anti-Corruption Layer) | **Core** | ⚠️ Booking wired | `shared/acl/` |
| Core enforcement (warn/block) | **Core** | ✅ warn | `core_enforcement.py` |
| Event catalog (machine-readable) | **Core** | ✅ | `event_catalog.py` |
| Legacy route map | **Core** | ✅ | `legacy_route_map.py` |
| Plugin registry document | **Core** | ✅ R1-F2 | `/v1/platform/plugin-registry` |
| Constitution / ADR / RFC process | **Core** | ✅ | `docs/` |
| Definition of Done arquitetural | **Core** | ✅ | `DefinitionOfDone-Architecture.md` |

### Plugin Engine

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Manifest loader (YAML) | **Core** | ✅ | `core/plugin/` |
| Plugin registry runtime | **Core** | ✅ | 3 manifests |
| Plugin hooks (event handlers) | **Core** | ✅ | manifest `hooks` |
| Plugin SDK CLI | **Future** | 🔜 | Release 6 |
| Plugin certification | **Future** | 🔜 | Release 5 |

### SDK & Developer Experience

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| TypeScript SDK (`@coreflow/sdk`) | **Core** | ✅ | `packages/coreflow-sdk/` |
| OpenAPI / Swagger | **Core** | ✅ | `/docs` |
| Developer Portal (docs) | **Core** | ✅ Este doc set | `docs/DeveloperPortal.md` |
| Public API + webhooks | **Future** | 🔜 | Release 6 |
| CLI (`coreflow`) | **Future** | 🔜 | Release 6 |

### Storage & Media

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Static file upload | **Core** | ⚠️ Básico | FastAPI StaticFiles |
| S3 / CDN sync | **Core** | ✅ | mobile CDN services |
| Storage abstraction port | **Future** | 🔜 | — |

### Mobile DevOps

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| EAS build/submit | **Core** | ✅ | CF-15+ |
| OTA updates + canary | **Core** | ✅ | CF-24/25 |
| Terraform CDN/CloudFront | **Core** | ✅ | `infra/terraform/` |
| Offline sync | **Experimental** | Spike R4 | — |
| Flutter client | **Future** | 🔜 | Opcional — Expo primary |

### Observability

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Prometheus metrics | **Core** | ✅ | `prometheus_metrics.py` |
| HTTP layer telemetry | **Core** | ✅ | `legacy_telemetry.py` |
| Grafana dashboards as code | **Core** | ✅ | observability module |
| Alertmanager rules as code | **Core** | ✅ | CF-24 |
| OpenTelemetry | **Core** | ⚠️ Opcional | `telemetry.py` |
| Runtime observability stack | **Future** | 🔜 | Release 3 docker stack |

### Marketplace & Ecosystem

| Capacidade | Classificação | Estado | Evidência |
|------------|---------------|--------|-----------|
| Marketplace API stub | **Experimental** | Stub | `marketplace_service.py` |
| Plugin install per tenant | **Future** | 🔜 | Release 5 |
| Publisher billing | **Future** | 🔜 | Release 5 |
| Partner program | **Future** | 🔜 | Release 6 |

---

## Heatmap por Release

| Capacidade area | R1 ✅ | R2 | R3 | R4 | R5 | R6 | R7 |
|-----------------|-------|----|----|----|----|----|-----|
| Governance | ████ | ██ | ██ | ██ | ██ | ██ | ██ |
| Booking pure core | ██ | ████ | ███ | ██ | ██ | ██ | ██ |
| Resource Engine | █ | ████ | ███ | ██ | ██ | ██ | ██ |
| Plugin separation | ██ | ████ | ███ | ████ | ████ | ███ | ██ |
| AI Platform | █ | ██ | ████ | ████ | ███ | ███ | ███ |
| Business Platform | █ | ██ | ████ | ███ | ███ | ███ | ████ |
| Marketplace | █ | █ | ██ | ███ | ████ | ████ | ███ |
| Developer Platform | ██ | ███ | ███ | ████ | ████ | ████ | ████ |
| International | █ | █ | ██ | ██ | ███ | ███ | ████ |

---

## Referências

- `docs/PlatformVision.md`
- `docs/BoundedContexts.md`
- `docs/CoreVsPlugins.md`
- `docs/PlatformRoadmap2030.md`
- `docs/ArchitectureAssessment.md`
