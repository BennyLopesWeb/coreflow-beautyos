# Core Framework

Componentes compartilhados por todos os plugins.

## Módulos backend (`backend/app/modules/`)

| Módulo | Responsabilidade |
|--------|------------------|
| identity | Auth, companies, RBAC |
| catalog | Catalog, Offering |
| booking | Booking genérico |
| scheduling | Location, Worker, Resource, ScheduleBlock |
| customer | Customer |
| payments | Payment + PaymentProviderPort |
| waitlist | Waitlist |
| order / invoice | Order, Invoice |
| asset / inventory | Asset, Inventory |
| workflow | WorkflowEngine YAML |
| push | Device tokens, push, deep links |
| marketplace | Marketplace stub |
| observability | Grafana, Alertmanager as code |
| mobile | EAS, CDN, Terraform (platform ops) |
| ai | LLM factory (evoluir para AI Platform) |

## Shared kernel

- `backend/app/shared/kernel/` — TenantContext, RBAC
- `backend/app/shared/events/` — Event bus, outbox, Kafka, DLQ
- `backend/app/core/metamodel/concepts.py` — CoreConcept enum

## O que NÃO alterar sem RFC

- Contratos `/v1/*` publicados
- JWT claims (`company_id`, `role`)
- Plugin manifest schema v1
- Eventos Avro versionados em `backend/schemas/events/avro/`
