# CoreFlow — Developer Portal

**Documento:** `docs/DeveloperPortal.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Estratégico — guia para extensão da plataforma  
**Audiência:** Desenvolvedores internos, parceiros ISV, integradores

> Portal web dedicado (`developers.coreflow.app`) é **Future (Release 6)**. Este documento é a especificação funcional e guias práticos até lá.

---

## Pré-requisitos

| Item | Requisito |
|------|-----------|
| Runtime | Python 3.11+, Node 18+ |
| Repo | Clone CoreFlow monorepo |
| Leitura obrigatória | `CONSTITUTION.md`, `CoreMetaModel.md`, `CoreVsPlugins.md` |
| Processo | RFC → ADR → Aprovação → Fase incremental |

---

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt
pytest -o addopts=

# Frontend
cd frontend && npm install && npx expo start

# SDK
cd packages/coreflow-sdk && npm install && npm run build
```

API local: `http://localhost:8000/docs`  
Platform health: `GET /v1/platform/health`

---

## 1. Criar Plugin

### Quando criar

Novo vertical (Sports, Clinic, Pet) ou extensão significativa de terminologia/features.

### Passos

1. **Validar escopo** — preencher matriz `docs/CoreVsPlugins.md`
2. **Copiar template** — `backend/plugins/beauty/manifest.yaml` como base
3. **Definir manifest** em `backend/plugins/{plugin_id}/manifest.yaml`:

```yaml
plugin_id: sports
name: SportsOS
version: "1.0.0"
product_name: SportsOS
terminology:
  worker: Instrutor
  resource: Quadra
  catalog: Modalidade
  offering: Plano
  booking: Reserva
features:
  - deposit_payment
  - recurring_booking
hooks:
  booking.created: app.plugins.sports.hooks.on_booking_created
sdk:
  routes:
    bookings: /v1/bookings
    catalogs: /v1/catalogs
```

4. **Implementar hooks** em `backend/app/plugins/{plugin_id}/hooks/` (🔜 estrutura formal R2)
5. **Registrar testes** — manifest validation + terminology resolution
6. **Documentar** — ADR se novo padrão; atualizar Plugin Registry via API

### Validação

```bash
curl http://localhost:8000/v1/platform/plugin-registry
curl http://localhost:8000/v1/plugins/sports
curl http://localhost:8000/v1/plugins/config/by-company/demo
```

### Checklist

- [ ] Nenhum import de models legado beauty no plugin genérico
- [ ] Terminology cobre todos concepts usados na UI
- [ ] Features declaradas no manifest — não hardcoded
- [ ] Mobile block preenchido se app whitelabel

---

## 2. Criar Evento

### Convenção

`{aggregate}.{action}` — schema Avro `{event}.v{major}.avsc` em `backend/schemas/events/`

### Passos

1. **Verificar** event catalog existente: `GET /v1/platform/event-catalog`
2. **Propor RFC** se evento cross-context novo
3. **Definir payload** — tenant-scoped, sem PII desnecessário
4. **Criar schema Avro** (se Kafka externo)
5. **Publicar** via `DomainEvent` + outbox:

```python
from app.shared.events.domain_event import DomainEvent
from app.shared.events.event_bus import event_bus

event = DomainEvent(
    event_type="booking.created",
    company_id=company_id,
    aggregate_id=str(booking_id),
    aggregate_type="Booking",
    payload={"customer_id": customer_id, "scheduled_at": iso_dt},
)
event_bus.publish(db, event)
```

6. **Registrar** em `shared/events/event_catalog.py` (status: implemented)
7. **Atualizar** `docs/architecture/EventCatalog.md`
8. **Testes** — handler mock + outbox assertion

### Consumir evento

- **Workflow:** YAML trigger em `backend/workflows/`
- **Handler:** registrar em manifest `hooks` ou `modules/*/application/handlers.py`
- **Kafka:** outbox worker dispatch automático

---

## 3. Criar Adapter (ACL)

### Quando

Integração Core ↔ Legado ou Core ↔ sistema externo.

### Estrutura

```
shared/acl/{context}_port.py      # Protocol (Port)
modules/{context}/infrastructure/ # Adapter implementation (🔜 R2)
```

### Exemplo (Booking — existente R1-F2)

```python
# Port: shared/acl/booking_port.py
class BookingPort(Protocol):
    def create_booking_via_legacy(self, ...) -> Any: ...

# Adapter: LegacyBookingAdapter delega ReservationService
adapter = LegacyBookingAdapter(db)
booking = adapter.create_booking_via_legacy(...)
```

### Regras

- Application layer depende **somente** do Port (Protocol)
- Adapter registra telemetria ACL (`ArchitectureMetricsStore`)
- Feature flag protege path novo (`booking.core.enabled`)
- **Nunca** SQLAlchemy ou HTTP no domain layer

---

## 4. Criar Porta (Port)

### Template

```python
from typing import Protocol, Optional

class CustomerQueryPort(Protocol):
    """
    Port hexagonal para consultas de cliente.

    Args:
        customer_id: ID core_customers.
        company_id: Tenant.

    Returns:
        DTO cliente ou None.
    """
    def get_by_id(self, customer_id: int, company_id: int) -> Optional[CustomerDTO]: ...
```

### Onde colocar

| Tipo | Path |
|------|------|
| ACL legado | `shared/acl/` |
| Domínio core | `modules/{context}/application/ports/` (🔜 R2) |
| Infra externa | `modules/{context}/application/ports/` |

### Wiring

FastAPI deps ou factory no application service — injeção no `__init__`.

---

## 5. Criar Dashboard (Grafana)

### Existente (R1-F2)

`GrafanaArchitectureDashboardService` — dashboard `coreflow-api-layers`

### Passos

1. Definir panels PromQL em service dedicado estendendo padrão existente
2. Export JSON: `GET /v1/platform/grafana/dashboard/layers`
3. Admin export: `POST /v1/platform/grafana/dashboard/layers/export`
4. Commit artefato em `infra/grafana/dashboards/`
5. Documentar queries em `docs/ArchitectureMetrics.md`

### Métricas disponíveis

- `coreflow_http_requests_total{layer, method, status_class}`
- `coreflow_http_request_duration_seconds{layer}`
- Architecture metrics store (in-process) via `/v1/platform/architecture-metrics`

---

## 6. Criar Workflow

### Definição YAML

Local: `backend/workflows/` (carregado por `WorkflowEngine.load_all()`)

```yaml
id: notify_on_deposit
trigger:
  event_type: payment.deposit.confirmed
steps:
  - action: notify_admin
    params:
      template: deposit_confirmed
  - action: approve_booking_if_pending
```

### Actions disponíveis

Consultar `modules/workflow/engine/` — expandir via ADR + registro de action catalog.

### Testes

```python
engine = WorkflowEngine()
engine.load_all()
runs = engine.process_event(db, domain_event)
assert runs[0].status == WorkflowRunStatus.COMPLETED
```

---

## 7. Criar AI Agent

### Regra constitucional

**Agents verticais → Plugin.** Core fornece apenas shell.

### Passos (plugin)

1. Declarar em manifest: `ai_capabilities: [crm_followup]`
2. Implementar agent em `plugins/{id}/agents/`
3. Usar `LLMService.get_provider()` — nunca OpenAI direto
4. Tools via ports (booking, customer) — não models legado
5. Publicar evento `ai.agent.invoked` (🔜)
6. Testes com `mock` provider

### Core shell (futuro Release 4)

```python
# Futuro — AgentRegistry
registry.register("beauty.crm_followup", BeautyCrmAgent())
```

---

## 8. Criar Integração (Webhook / External)

### Inbound (webhook)

- Router dedicado em `routers/webhook.py` ou módulo
- Validar assinatura (HMAC)
- Traduzir payload → DomainEvent ou Command
- Idempotency key obrigatório

### Outbound (🔜 Release 6)

- `WebhookSubscription` model
- Dispatch via outbox worker
- Retry + DLQ pattern (reutilizar Kafka DLQ infra)

### Payment provider

Implementar `PaymentProviderPort` — adapter Stripe/MercadoPago/Pix.

---

## 9. Criar Migration (Database)

### Processo

```bash
cd backend
alembic revision --autogenerate -m "add_core_resources_table"
alembic upgrade head
```

### Regras

- Tabelas core: prefixo `core_*`
- Sempre `company_id` em entidades tenant-scoped
- Nomenclatura inglês snake_case (Meta Model)
- Migration reversível quando possível
- ADR + update `CoreMetaModel.md` para novos conceitos

---

## 10. Criar Frontend Module

### Stack

Expo ~50, React Native, Expo Router — `frontend/`

### Padrão

1. Consumir **`@coreflow/sdk`** — nunca fetch raw para `/v1/*` em código novo
2. Resolver terminology: `GET /v1/plugins/config/by-company/{slug}`
3. Labels UI = `terminology.booking`, não strings hardcoded
4. Deep links via manifest `sdk.deep_links`

### Estrutura

```
frontend/app/           # Expo Router screens
frontend/src/services/  # Migrar legado → SDK gradualmente
packages/coreflow-sdk/  # Tipos + client HTTP
```

### Plugin-specific UI (futuro)

Config-driven layouts via manifest `ui:` block — gallery vs list, etc.

---

## APIs de referência para desenvolvedores

| API | Uso |
|-----|-----|
| `GET /v1/platform/health` | Saúde arquitetural |
| `GET /v1/platform/feature-flags` | Flags de migração |
| `GET /v1/platform/event-catalog` | Eventos disponíveis |
| `GET /v1/platform/legacy-route-map` | Mapa migração API |
| `GET /v1/platform/plugin-registry` | Plugins registrados |
| `GET /v1/plugins` | Manifests runtime |
| `GET /docs` | OpenAPI interativo |

---

## Suporte e governança

| Canal | Uso |
|-------|-----|
| RFC | Proposta de mudança estrutural |
| ADR | Decisão arquitetural registrada |
| PR Checklist | `docs/decisions/PR-Checklist.md` |
| DoD Arquitetural | `docs/decisions/DefinitionOfDone-Architecture.md` |

---

## Roadmap Developer Portal

| Release | Entrega |
|---------|---------|
| R2 | Plugin hook structure formal + exemplos sports stub |
| R4 | Workflow visual editor docs |
| R6 | Portal web + CLI `coreflow plugin init` |
| R6 | API pública + API keys |

---

## Referências

- `docs/EngineeringHandbook.md`
- `docs/CoreVsPlugins.md`
- `packages/coreflow-sdk/README.md`
- `backend/plugins/beauty/manifest.yaml`
- `docs/architecture/EventCatalog.md`
