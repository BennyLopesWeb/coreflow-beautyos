# ADR-005 — Core Framework: Limites e Responsabilidades

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2026-07-09 |
| **RFC** | RFC-001 (governança) |

## Contexto

CoreFlow evolui para plataforma multi-produto. Sem fronteiras claras, lógica vertical (beauty) contamina o core e impede novos plugins.

## Problema

O que **obrigatoriamente** pertence ao Core vs Plugin vs Legado (transitório)?

## Decisão

### Pertence OBRIGATORIAMENTE ao Core

| Domínio | Módulo / Path | Responsabilidade |
|---------|---------------|------------------|
| **Authentication** | `modules/identity/` | Login, JWT, refresh, sessão |
| **Authorization** | `shared/kernel/rbac.py`, identity | RBAC, roles, permissions |
| **Tenant / Company** | identity, `TenantContext` | Multi-tenant row-level |
| **Location** | `modules/scheduling/` | Unidade física genérica |
| **Worker** | `modules/scheduling/` | Quem executa serviço |
| **Resource** | `modules/scheduling/`, Resource Engine | O que é reservado |
| **Customer** | `modules/customer/` | Cliente final genérico |
| **Booking** | `modules/booking/` | Reserva genérica |
| **Service Catalog** | `modules/catalog/` | Catalog + Offering |
| **Payment** | `modules/payments/` + PaymentProviderPort | Pagamento abstrato |
| **Order** | `modules/order/` | Pedido genérico |
| **Invoice** | `modules/invoice/` | Fatura genérica |
| **Inventory / Asset** | `modules/inventory/`, `asset/` | Estoque e ativos |
| **Waitlist** | `modules/waitlist/` | Fila de espera |
| **Workflow** | `modules/workflow/` | Automação event-driven |
| **Notification / Push** | `modules/push/` | Notificação, deep links |
| **Event Infrastructure** | `shared/events/` | Bus, outbox, Kafka, DLQ |
| **Plugin Framework** | `core/plugin/` | Registry, manifest loader |
| **Observability** | `modules/observability/`, prometheus | Métricas, dashboards as code |
| **Platform Mobile Ops** | `modules/mobile/` | EAS, CDN, Terraform (não UI) |
| **Marketplace (platform)** | `modules/marketplace/` | Instalação de plugins (evoluir) |
| **AI Platform (shell)** | `modules/ai/` | Provider registry, prompt engine — **não agents verticais** |
| **Storage (abstração)** | ports futuros | Object storage port |
| **Analytics (shell)** | futuro | Métricas agregadas cross-tenant |
| **Audit** | futuro R3 | Audit trail transversal |
| **Shared** | `shared/kernel/`, `shared/acl/` | Tenant, RBAC, ACL |

### NÃO pertence ao Core (Plugin ou Legado)

| Item | Onde |
|------|------|
| Terminologia Tranca/Modelo | Plugin beauty manifest |
| BeautyAgent, CRM beauty | Plugin beauty (`ai/` agent vertical) |
| Regras pricing beauty-specific | Plugin hooks |
| UI Expo trancista | `frontend/` como cliente beauty |
| Routers legado PT-BR | Transitório — sunset via RFC-002 |
| Terraform CDN policies | Platform ops OK no core mobile module |

### Shared vs Core

**Shared** = kernels transversais sem regra de negócio de vertical (tenant, events, acl).  
**Core modules** = bounded contexts com entidades `core_*` e API `/v1/*`.

## Consequências

- Novos conceitos passam por ADR + CoreMetaModel.md
- Código beauty-specific no core deve migrar para plugin (Backlog EPIC-AI-001)

## Benefícios

- Fronteiras claras para novos produtos
- Reviews objetivos (Cinco Perguntas da Constituição)

## Trade-offs

- Período de duplicação legado/core até Strangler completar

## Alternativas descartadas

- Core monolítico com `if plugin == beauty` — rejeitado (viola Plugin First)

## Referências

- `docs/CONSTITUTION.md` Artigo III
- `docs/CoreMetaModel.md`
- `docs/ArchitectureAssessment.md` §22
