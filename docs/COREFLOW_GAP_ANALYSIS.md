# CoreFlow Platform — Análise de Gap vs Documentação Final

**Data:** Julho 2026 · **Versão código:** `0.3.0-sprint3`  
**Veredicto:** A visão final é **correta e alcançável**. O projeto já caminha nessa direção (Sprints CF-0→3), mas **~35% da doc existe** e **~40% do core está implementado** em modo Strangler Fig. O maior gap não é código Beauty — é **formalizar o coração (Meta Model + Resource Engine + Scheduling Engine)** e **reorganizar a documentação** nos 21 capítulos propostos.

---

## 1. Resumo executivo

| Dimensão | Situação atual | Meta final | Gap |
|----------|----------------|------------|-----|
| **Documentação SAB (00–20)** | 11 arquivos, numeração antiga | 21 capítulos completos | **~65% doc faltando** |
| **Meta Model (ORM + API)** | 7 entidades `core_*` + enum | 15+ conceitos universais | **~45% implementado** |
| **Resource Engine** | `CoreResource` básico (chair, cap=1) | Hierarquia + tipos plugáveis | **~20%** |
| **Scheduling Engine** | Availability parcial + legado | Motor completo 12 capacidades | **~35%** |
| **Plugin Framework** | Loader + manifest mínimo | SDK + menus/routes/AI/events | **~25%** |
| **AI Platform** | `AgenteService` rule-based | Módulo Chat/Vision/Agents/RAG | **~10%** |
| **Event Driven** | Bus in-memory, 3 eventos | Automação + Workflow visual | **~25%** |
| **Multi-tenant** | Company + RBAC | Branch/Dept/White Label | **~50%** |
| **Mobile / Sync** | Expo web, sem offline | Flutter + Sync Engine | **~5%** |
| **Marketplace / Public SDK** | — | Plugins, temas, prompts | **0%** |

**Decisão arquitetural central (Core vs Domínio):** já adotada na prática via Strangler Fig + plugins, mas **não está totalmente enforced no código** — ~60% das regras ainda vivem em `services/` legado (`Tranca`, `Agendamento`).

---

## 2. Mapa capítulo a capítulo (00–20)

Legenda: ✅ existe · ⚠️ parcial · ❌ ausente · 📝 conteúdo em outro arquivo

| # | Capítulo proposto | Status doc | Status código | Onde está hoje | O que ajustar |
|---|-------------------|------------|---------------|----------------|---------------|
| **00** | Executive Summary | ❌ | — | — | Criar `docs/00-EXECUTIVE-SUMMARY/` — 1 página: visão, veredicto, % reaproveitamento, roadmap |
| **01** | Vision | ⚠️ | — | `docs/00-VISION/Vision.md` | Renumerar pasta → `01-VISION/`; expandir filosofia Core vs Domínio |
| **02** | Business Model | ❌ | — | — | SaaS tiers, marketplace revenue, plugin economics |
| **03** | Market Position | ❌ | — | trechos em `BEAUTYOS_BLUEPRINT.md` | Consolidar Beauty/Sports/Clinic positioning |
| **04** | Architecture | ⚠️ | ⚠️ | `docs/01-ARCHITECTURE/`, `BEAUTYOS_ARCHITECTURE.md` | Unificar num único capítulo; diagrama Core Engine vs Plugins |
| **05** | Domain Model | ⚠️ | ⚠️ | `DOCUMENTACAO.md`, ADR-001 | **Capítulo central** — diagrama Business→Company→…→Notification |
| **06** | Plugin Framework | ⚠️ | ⚠️ | `docs/03-PLUGINS/`, `core/plugin/` | Expandir manifest (menus, routes, permissions, ai, events) |
| **07** | Meta Model | ⚠️ | ⚠️ | `core/metamodel/concepts.py`, ADR-001 | **Coração** — doc + ORM completo (ver §3) |
| **08** | AI Platform | ❌ | ⚠️ | `AgenteService`, `AgentTask` | Novo módulo `modules/ai/` |
| **09** | Scheduling Engine | ❌ | ⚠️ | `modules/scheduling/`, legado | Doc + extrair motor do legado (ver §5) |
| **10** | Marketplace | ❌ | ❌ | — | Futuro — só doc estratégica |
| **11** | Mobile Strategy | ❌ | ⚠️ | Expo frontend | Doc Flutter/offline/sync |
| **12** | Event Driven | ❌ | ⚠️ | `shared/events/` | Doc + outbox + handlers por domínio |
| **13** | Security | ❌ | ⚠️ | JWT, RBAC | OWASP, audit log, secrets |
| **14** | Multi Tenant | ⚠️ | ⚠️ | `Company`, `UserCompany` | Branch, Department, isolamento row-level |
| **15** | SDK | ❌ | ❌ | — | Plugin SDK + Public SDK |
| **16** | Roadmap | ⚠️ | — | `COREFLOW_ANALYSIS.md`, Blueprint | Roadmap unificado por trimestre |
| **17** | Sprints | ⚠️ | — | `docs/04-SPRINTS/Sprint00–03` | Renumerar → `17-SPRINTS/`; redefinir Sprint 0 (ver §8) |
| **18** | Cursor Prompts | ❌ | — | — | `.cursor/rules`, prompts por módulo |
| **19** | ADR | ⚠️ | — | `docs/06-ADR/` (2 ADRs) | Renumerar → `19-ADR/`; ADRs para Resource, Scheduling, AI |
| **20** | Future Vision | ❌ | — | trechos em Blueprint | Workflow Builder, Form Builder, White Label |

### Reorganização física recomendada

```
docs/
├── 00-EXECUTIVE-SUMMARY/
├── 01-VISION/              ← mover 00-VISION
├── 02-BUSINESS-MODEL/
├── 03-MARKET-POSITION/
├── 04-ARCHITECTURE/        ← mover 01-ARCHITECTURE
├── 05-DOMAIN-MODEL/
├── 06-PLUGIN-FRAMEWORK/    ← mover 03-PLUGINS + expandir
├── 07-META-MODEL/          ← ADR-001 + diagramas
├── 08-AI-PLATFORM/
├── 09-SCHEDULING-ENGINE/
├── 10-MARKETPLACE/
├── 11-MOBILE-STRATEGY/
├── 12-EVENT-DRIVEN/
├── 13-SECURITY/
├── 14-MULTI-TENANT/
├── 15-SDK/
├── 16-ROADMAP/
├── 17-SPRINTS/             ← mover 04-SPRINTS
├── 18-CURSOR-PROMPTS/
├── 19-ADR/                 ← mover 06-ADR
└── 20-FUTURE-VISION/
```

Arquivos raiz (`BEAUTYOS_*`, `COREFLOW_ANALYSIS.md`) → **arquivar ou absorver** nos capítulos 04–07 e 16, evitando duplicidade.

---

## 3. Meta Model — o coração (gap detalhado)

### 3.1 Cadeia universal proposta

```
Business → Company → Location → Resource → Worker
    → Service → Booking → Customer → Order → Invoice
    → Payment → Asset → Inventory → Notification
```

### 3.2 Estado atual no código

| Conceito | Enum `CoreConcept` | Tabela `core_*` | API `/v1/*` | Legado ativo | Gap |
|----------|-------------------|-----------------|-------------|--------------|-----|
| **Business** | ❌ | ❌ | ❌ | — | Novo: agrupador acima de Company (franquia/holding) |
| **Company** | ✅ | `companies` | `/companies` | ✅ | OK — falta Branch |
| **Location** | ✅ | `core_locations` | `/v1/locations` | implícito | OK base — falta multi-unidade real |
| **Resource** | ✅ | `core_resources` | `/v1/resources` | implícito | Falta **Resource Engine** (tipos hierárquicos) |
| **Worker** | ✅ | `core_workers` | `/v1/workers` | `UserCompany` | OK base |
| **Service** | ✅ enum | ❌ (usa Catalog) | — | `Tranca` | **Unificar**: Catalog = agrupador; Service = tipo de serviço |
| **Offering** | ✅ | `core_offerings` | `/v1/catalogs/.../offerings` | `ServiceImage` | OK via Strangler |
| **Catalog** | ✅ | `core_catalogs` | `/v1/catalogs` | `Tranca` | OK |
| **Booking** | ✅ | `core_bookings` | `/v1/bookings` | `Agendamento` | CQRS parcial (1 command) |
| **Customer** | ✅ enum | ❌ | — | `clientes` | Falta `core_customers` + sync |
| **Order** | ❌ | ❌ | ❌ | — | Novo aggregate (Booking → Order comercial) |
| **Invoice** | ❌ | ❌ | ❌ | — | Novo (NF / recibo) |
| **Payment** | ✅ enum | ❌ | — | `payments` | Falta `core_payments` + sync |
| **Asset** | ✅ enum | ❌ | ❌ | — | Novo (cabelo sintético, bola, etc.) |
| **Inventory** | ❌ | ❌ | ❌ | — | Novo |
| **Notification** | ❌ | ❌ | — | `notification_logs` | Falta `core_notifications` + port |
| **ScheduleBlock** | ✅ | `core_schedule_blocks` | — | `schedules` | Sync parcial |
| **Waitlist** | ✅ enum | ❌ | — | `fila` | Falta `core_waitlist_entries` |
| **OperationalQueue** | ✅ enum | ❌ | — | `queue_entries` | Falta `core_queue_entries` |
| **FinanceEntry** | ✅ enum | ❌ | — | `financeiro` | Falta sync |

### 3.3 Ajustes prioritários (Meta Model)

1. **Documentar** cadeia completa em `07-META-MODEL/` com diagrama e mapeamento por plugin (Beauty/Sports/Clinic).
2. **Completar ORM genérico** (fase CF-4→6): `core_customers`, `core_payments`, `core_waitlist`, `core_queue`, `core_services` (separar de Catalog).
3. **Enforcement**: novas escritas só via `/v1/*` + CQRS; legado read-only com Sunset (já iniciado CF-3).
4. **Manifest**: expandir `metamodel_mappings` para Asset, Inventory, Order, Invoice.

---

## 4. Resource Engine (gap)

### Visão
Tudo é Resource. Tipos: Professional, Room, Court, Vehicle, Equipment, Machine. Scheduling reserva Resources sem saber o domínio.

### Atual
- `CoreResource` com `ResourceType`: chair, court, room, generic
- Capacidade = 1 fixo no beauty
- Sem hierarquia Location → Resource → sub-resource
- Conflitos calculados via `Agendamento` legado, não via `core_schedule_blocks`

### Ajustes
| Prioridade | Ação |
|------------|------|
| P0 doc | Capítulo `09` ou seção em `07` — Resource Engine spec |
| P1 código | `ResourceType` extensível via plugin manifest |
| P1 código | `SchedulingEngine` consulta `core_schedule_blocks` + capacity |
| P2 código | Resource allocation API: `POST /v1/resources/{id}/allocate` |
| P3 | Multi-resource bookings (N cadeiras, quadra + árbitro) |

---

## 5. Scheduling Engine (gap)

### Visão (12 capacidades)
Availability → Reservation → Conflict → Capacity → Recurring → Waitlist → Check-in/out → Cancellation → No-show → Pricing → Notification → Audit

### Atual

| Capacidade | Status | Onde |
|------------|--------|------|
| Availability | ⚠️ | `SchedulingAvailabilityService` → legado |
| Reservation | ⚠️ | `CreateBookingCommand` + legado |
| Conflict Detection | ⚠️ | `ScheduleService`, `DisponibilidadeService` |
| Capacity | ⚠️ | Implícito cap=1 |
| Recurring | ❌ | — |
| Waiting List | ⚠️ | `Fila` legado |
| Check-in/out | ❌ | — |
| Cancellation | ⚠️ | legado |
| No-show | ❌ | — |
| Pricing | ⚠️ | snapshot na reserva |
| Notification | ⚠️ | mock |
| Audit | ❌ | — |

### Ajustes
1. Extrair **`modules/scheduling/engine/`** com interface única:
   - `check_availability(resource_ids, window, duration)`
   - `create_reservation(...)`, `detect_conflicts(...)`, etc.
2. Legado vira **adapter** do engine (Strangler).
3. Documentar state machine de Booking em `09-SCHEDULING-ENGINE/`.

---

## 6. Plugin Framework & SDK (gap)

### Manifest atual vs proposto

| Campo proposto | Manifest beauty | Gap |
|----------------|-----------------|-----|
| `plugin.name/version` | ✅ | — |
| `terminology` | ✅ | — |
| `metamodel_mappings` | ✅ parcial | Asset, Inventory, Order |
| `menus` | ❌ | UI admin dinâmica |
| `permissions` | ❌ | RBAC por plugin |
| `entities` | ❌ | schema extensível |
| `routes` | ❌ | registro dinâmico FastAPI |
| `dashboard` | ❌ | widgets |
| `reports` | ❌ | — |
| `ai` | ❌ | agents declarativos |
| `events` | ❌ | subscribe/publish |

### Ajustes
1. Evoluir `PluginManifest` Pydantic com campos opcionais.
2. `PluginRegistry` carrega routes/handlers declarados (CF-5).
3. Capítulo `06-PLUGIN-FRAMEWORK/` + `15-SDK/` com tutorial "Hotel Plugin".
4. Template `backend/plugins/_template/manifest.yaml`.

---

## 7. AI Platform & Agents (gap)

### Atual
- `AgenteService`: rule-based (lembrete pagamento, reativar cliente)
- `AgentTask` model
- Sem LLM, Vision, RAG, Memory

### Ajustes (doc + código)
```
modules/ai/
  platform/     ports: ChatPort, VisionPort, EmbeddingPort
  agents/     BeautyAgent (plugin beauty registra)
  automation/ escuta booking.created → WhatsApp + CRM
  memory/     tenant-scoped context
```
Documentar em `08-AI-PLATFORM/` e `12-EVENT-DRIVEN/` (Business Automation).

---

## 8. Capítulos transversais

| Capítulo | Gap principal | Ajuste |
|----------|---------------|--------|
| **12 Event Driven** | 3 eventos, bus sync | Outbox pattern, catalog de eventos, handler registry |
| **13 Security** | JWT básico | Audit trail, rate limit, OWASP checklist |
| **14 Multi Tenant** | Company flat | Branch, Department, row-level security |
| **White Label** (Future) | logo_url only | tema, domínio, e-mail — doc em 20-FUTURE-VISION |
| **Workflow Engine** | — | doc only Sprint 8+; integra Event + AI |
| **Form/Dashboard Builder** | — | doc only; Odoo-like |
| **Sync Engine / Mobile** | Expo web | doc 11; Flutter Sprint 10+ |
| **Marketplace / Public SDK** | — | doc 10 + 15 estratégico |

---

## 9. Sprint 0 — redefinição proposta vs realidade

A visão final expande Sprint 0 para **Architecture Foundation** completo. Situação honesta:

| Item Sprint 0 expandido | CF-0..3 | Próximo sprint |
|-------------------------|---------|----------------|
| Monorepo + ADR | ✅ | — |
| Hexagonal + DDD | ⚠️ identity only | Extrair scheduling, catalog, booking |
| CQRS | ⚠️ 1 command | Commands por aggregate |
| Event Driven | ⚠️ in-memory | Outbox CF-5 |
| Plugin Engine | ⚠️ loader v0 | SDK CF-6 |
| Meta Model | ⚠️ 7 tabelas | Completar §3.3 |
| Resource Engine | ⚠️ proto | CF-4 |
| Scheduling Engine | ⚠️ proto | CF-4 |
| AI Platform | ❌ | CF-7 |
| Observability | ❌ | OpenTelemetry CF-5 |
| MySQL Docker | ✅ CF-3 | CI MySQL CF-4 |
| Kubernetes Ready | ❌ | doc 04 |
| Dev Containers | ❌ | CF-5 |
| Feature Flags | ❌ | CF-6 |
| White Label | ❌ | CF-10+ |

**Recomendação:** não reescrever Sprint 0 retroativamente — criar **`17-SPRINTS/Sprint00-REFACTOR.md`** que documenta a visão expandida como **"Sprint 0 Target State"** e mapeia CF-0..3 como **fase 1 alcançada**.

---

## 10. Código — plano de ajuste (priorizado)

### Fase A — Documentação (1–2 semanas, sem breaking changes)
1. Reorganizar `docs/` na numeração 00–20 (pastas + README stub por capítulo).
2. Consolidar `BEAUTYOS_*` + `COREFLOW_ANALYSIS.md` nos capítulos corretos.
3. Atualizar `COREFLOW_ANALYSIS.md` (está desatualizado: diz Plugin 0%, CQRS 0%).
4. Criar `07-META-MODEL/README.md` com diagrama Mermaid da cadeia universal.
5. Criar `09-SCHEDULING-ENGINE/README.md` com matriz de capacidades.

### Fase B — Core enforcement (4–6 semanas)
6. `core_customers` + sync + `/v1/customers`
7. Scheduling Engine extrai legado → `modules/scheduling/engine/`
8. Resource types via manifest; conflitos via `core_schedule_blocks`
9. `POST /v1/bookings` no fluxo frontend completo
10. Outbox + mais eventos (`booking.approved`, `payment.confirmed`)

### Fase C — Platform (8–16 semanas)
11. Plugin manifest completo + route loader
12. `modules/ai/` + BeautyAgent
13. Workflow engine (config YAML → event handlers)
14. Flutter + Sync Engine (doc 11 implementado)

---

## 11. O que NÃO mudar (ativos preservados)

- Ciclo reserva Beauty (pending_payment → approval → schedule → paid) — **ouro de domínio**
- `IdentityApplicationService` + multi-tenant
- Strangler Fig (legado + v1 paralelos)
- 50 testes automatizados
- Plugin beauty como prova de conceito
- Snapshot comercial em bookings

---

## 12. Conclusão

A documentação final proposta **não contradiz** o que foi construído — **eleva o nível de abstração** do que já existe. O projeto está na transição correta:

```
BeautyOS (produto)  →  CoreFlow (plataforma)  →  Marketplace (ecossistema)
         ↑                        ↑                           ↑
    CF-0..3 feito          CF-4..7 necessário          CF-8+ visão
```

**Maior acréscimo imediato:** capítulos **07 Meta Model**, **09 Scheduling Engine**, **06 Plugin Framework** — em doc **e** código.

**Maior diferencial arquitetural:** separar Core (Resource, Booking, Event) de Domínio (manifest beauty) — **enforcement** no código, não só na documentação.

---

*Próximo passo sugerido:* executar **Fase A** (reorganizar docs/) e **CF-4** (Scheduling Engine + Resource Engine no código).
