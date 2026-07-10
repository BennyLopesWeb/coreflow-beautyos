# CoreFlow Platform — Análise Estratégica vs BeautyOS

**Build Once. Configure Everywhere.**

| | |
|---|---|
| **Autor da análise** | Engenharia BeautyOS / CoreFlow |
| **Data** | Julho 2026 |
| **Veredicto** | **EVOLUIR, não reescrever do zero** |
| **Reaproveitamento estimado** | **65–75%** do backend + **100%** do conhecimento de domínio |

Documentos relacionados: `BEAUTYOS_ARCHITECTURE.md` · `BEAUTYOS_MIGRATION.md` · `DOCUMENTACAO.md`

---

## 1. O que mudou na visão

| BeautyOS v3.0 | CoreFlow Platform |
|---------------|-------------------|
| Produto SaaS para beleza | **Framework** que gera produtos (BeautyOS, SportsOS, ClinicOS…) |
| Módulos DDD por domínio | **Core genérico** + **Plugins** que especializam |
| Tranca, ServiceImage, Agendamento | **Metamodelo**: Resource, Service, Booking, Worker, Customer… |
| Vertical trancista piloto | Beauty = **plugin #1** sobre o mesmo engine |
| Sprint 0 = features parciais | **Sprint 0 = só arquitetura** (CI, monorepo, plugin loader) |

**Conclusão:** CoreFlow não invalida o trabalho feito — **recontextualiza** BeautyOS como primeiro plugin sobre um núcleo maior.

---

## 2. Mapa de alinhamento arquitetural

```
                    CoreFlow SAB (visão)
                    ───────────────────
                    API First          ✅ 80% alinhado
                    AI First           ⚠️ 15% (proto agente)
                    Domain First       ⚠️ 50% (models acoplados a SQLAlchemy)
                    Hexagonal          ✅ 60% (identity + ports payments)
                    Event Driven       ✅ 40% (bus in-memory, 3 eventos)
                    Plugin First       ❌ 0% (não existe plugin loader)
                    Modular Monolith   ✅ 70%
                    Multi-tenant       ✅ 85%
                    CQRS               ❌ 0%
```

**Vocês já estavam construindo CoreFlow sem o nome** — faltam o **metamodelo genérico** e a **camada de plugins**.

---

## 3. Metamodelo CoreFlow ↔ código atual

Sua sugestão do **metamodelo** é o diferencial real. Mapeamento honesto:

| Conceito CoreFlow | Implementação atual | Reaproveitar? |
|-------------------|---------------------|---------------|
| **Company** | `Company`, multi-tenant, RBAC | ✅ **Sim — direto** |
| **User** | `User`, JWT, memberships | ✅ **Sim — módulo identity/** |
| **Customer** | `Cliente` (telefone único) | ✅ **Sim — renomear + tags/fotos** |
| **Worker** | `User.is_superuser` / profissional implícito | ⚠️ **Extrair entidade Worker** |
| **Location** | — | ❌ **Novo** (unidade física do salão) |
| **Resource** | Capacidade única implícita (1 cadeira) | ⚠️ **Formalizar** (Resource = cadeira, quadra, sala) |
| **Catalog** | — | ❌ **Novo** (agrupador genérico) |
| **Service** | `Tranca` (categoria) | ⚠️ **Generalizar** → CatalogCategory ou ServiceGroup |
| **ServiceOffering** | `ServiceImage` (preço, duração, sinal) | ⚠️ **Generalizar** → Service + variantes |
| **Booking** | `Agendamento` + status completos | ✅ **Sim — lógica é ouro** |
| **ScheduleBlock** | `Schedule` | ✅ **Sim** |
| **Availability** | `AgendaDia`, `DisponibilidadeService` | ✅ **Sim — Scheduling Engine** |
| **Waitlist** | `Fila` | ✅ **Sim** |
| **OperationalQueue** | `QueueEntry` | ✅ **Sim** |
| **Payment** | `Payment`, sinal, mock Pix | ✅ **Sim — PaymentPort já existe** |
| **FinanceEntry** | `Financeiro` | ✅ **Sim — parcial** |
| **Asset** | — | ❌ **Novo** (inventory futuro) |
| **Notification** | `NotificationService` mock | ⚠️ **Port + adapter** |
| **AI Agent** | `AgenteService` rule-based | ⚠️ **Evoluir para AI module** |

### O que NÃO jogar fora (ativo estratégico)

1. **Ciclo de reserva completo** — pending_payment → approval → schedule → queue → paid  
2. **Snapshot comercial** na reserva (preço congelado)  
3. **Regras de disponibilidade** — slots 30 min, conflito, expiração  
4. **Fila dupla** — waitlist + operacional  
5. **Multi-tenant + RBAC** — `IdentityApplicationService`  
6. **Event bus** — base para CoreFlow event-driven  
7. **28+ testes** — evoluem com o metamodelo  

### O que precisa ser refeito (não reescrita total)

| Área | Ação |
|------|------|
| Models `Tranca` / `ServiceImage` | Introduzir **Catalog + Service + Offering** genéricos; Beauty plugin adiciona terminologia |
| `Agendamento` | Renomear/evoluir para **Booking** aggregate genérico |
| Estrutura de pastas | Migrar para `backend/src/core/`, `modules/`, `plugins/beauty/` |
| Plugin loader | **Novo** — Sprint 0 CoreFlow |
| CQRS | **Novo** — commands/queries separados por módulo |
| Frontend Expo | Manter temporário; alvo React no monorepo |
| Sprint 0 tooling | Docker, CI, OpenTelemetry, pre-commit — **complementar** |

---

## 4. Arquitetura alvo CoreFlow

```
                         CoreFlow Platform
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    Core Engine           Plugin Loader          Shared Kernel
         │                     │                     │
    ┌────┴────┐         ┌──────┴──────┐      events, tenant,
    │Scheduling│         │   beauty/   │      rbac, ports
    │ CRM      │         │   sports/   │
    │ Finance  │         │   clinic/   │
    │ Inventory│         └─────────────┘
    │ AI       │
    │ Notify   │
    └──────────┘
              │
    Metamodelo genérico
    Resource · Service · Booking · Customer · Worker · Location
              │
         Adapters (Hexagonal)
    MySQL · Redis · Kafka · Stripe · OpenAI · WhatsApp
```

**BeautyOS** = `plugins/beauty/` que configura:

```yaml
# plugins/beauty/manifest.yaml (conceito)
plugin_id: beauty
terminology:
  worker: Trancista
  resource: Cadeira
  service_group: Tipo de Trança
  offering: Modelo
segment: trancista
features: [vision_pricing, deposit_30pct, waitlist]
```

---

## 5. Estrutura de repositório proposta

```
coreflow/                          # renomear repo (ou monorepo novo)
├── docs/                          # sua árvore SAB completa
│   ├── 00-VISION/
│   ├── 01-ARCHITECTURE/
│   ├── 02-DOMAINS/
│   ├── 03-PLUGINS/
│   ├── 04-SPRINTS/
│   ├── 05-CURSOR/
│   ├── 06-ADR/
│   └── 07-STANDARDS/
├── backend/
│   └── src/
│       ├── core/                  # metamodelo + plugin loader
│       │   ├── domain/            # Booking, Service, Resource (genéricos)
│       │   ├── application/       # use cases genéricos
│       │   └── plugin/            # PluginRegistry, manifest loader
│       ├── shared/                # events, kernel (já existe)
│       ├── modules/               # engines verticais-agnósticos
│       │   ├── identity/          # ✅ migrar de app/modules/identity
│       │   ├── scheduling/      # AgendaDia, Disponibilidade, Schedule
│       │   ├── booking/           # Booking aggregate + waitlist + queue
│       │   ├── crm/
│       │   ├── finance/
│       │   ├── payments/
│       │   ├── notification/
│       │   ├── marketplace/
│       │   ├── analytics/
│       │   └── ai/
│       ├── plugins/
│       │   └── beauty/            # Tranca, Vision, terminologia
│       └── legacy/                # Strangler — código atual até migrar
├── apps/
│   └── web-admin/                 # React (futuro)
├── mobile/
│   └── coreflow_app/              # Flutter (Sprint 10)
├── docker-compose.yml
├── Makefile
└── .github/workflows/
```

---

## 6. Decisão: evoluir vs reescrever

### ❌ Reescrever tudo do zero

| Pró | Contra |
|-----|--------|
| Pastas limpas desde o dia 1 | Perde 6–9 meses de regras de negócio validadas |
| Metamodelo puro | BeautyOS para de funcionar durante meses |
| Sprint 0 “perfeito” | Risco de nunca chegar ao plugin Beauty |

### ✅ Evoluir (Strangler Fig) — **RECOMENDADO**

| Fase | Entrega | Duração |
|------|---------|---------|
| **CF-0** | Monorepo docs/, Docker, CI, ADR-001 Metamodelo, plugin loader v0 | 2–3 sem |
| **CF-1** | Metamodelo schema + aliases Beauty (Tranca→ServiceGroup) | 2–3 sem |
| **CF-2** | Migrar identity → `modules/identity` (já ~95%) | 1 sem |
| **CF-3** | Scheduling engine genérico (extrair DisponibilidadeService) | 2–3 sem |
| **CF-4** | Booking aggregate genérico (Agendamento→Booking) | 3–4 sem |
| **CF-5** | Plugin beauty (manifest, terminologia, vision) | 2 sem |
| **CF-6** | CQRS + Kafka/RabbitMQ (handlers assíncronos) | 3–4 sem |

**BeautyOS continua operacional** em cada fase via camada `legacy/` + API aliases.

---

## 7. Sprint 0 CoreFlow — gap analysis

| Entrega Sprint 0 | Status atual |
|------------------|--------------|
| Monorepo | ❌ repo único sem apps/ separados |
| Docker | ❌ |
| CI/CD GitHub Actions | ❌ |
| FastAPI | ✅ |
| React | ❌ (Expo web) |
| Flutter | ❌ |
| Hexagonal | ✅ parcial (identity, payment port) |
| DDD | ✅ parcial |
| Event Driven | ✅ in-memory bus |
| CQRS | ❌ |
| Modular Monolith | ✅ em progresso |
| JWT + RBAC | ✅ |
| Logging | ✅ |
| OpenTelemetry | ❌ |
| Swagger | ✅ /docs |
| Alembic | ❌ (migrate_schema SQLite) |
| Testes | ✅ 33 tests |
| Makefile | ❌ |
| Ruff/Black/Mypy/pre-commit | ❌ |
| ADR | ❌ (criar 06-ADR/) |
| Estrutura módulos | ✅ iniciada |
| Plugin Loader | ❌ **crítico Sprint 0** |
| AI Module skeleton | ⚠️ agente rule-based |
| Observabilidade | ❌ |

**Sprint 0 CoreFlow ≈ 35% concluído** — mas a parte **difícil de produto** (booking rules) já existe.

---

## 8. Metamodelo — schema conceitual

```sql
-- CORE (genérico)
companies, users, user_companies, customers
workers (user_id, company_id, specialties JSON)
locations (company_id, nome, endereco, geo)
resources (company_id, location_id, type, capacity)  -- cadeira, quadra, sala
catalogs (company_id, plugin_id, name)               -- agrupador
services (catalog_id, name, plugin_metadata JSON)    -- offering template
service_variants (service_id, price, duration, deposit_pct)  -- ex- ServiceImage
bookings (customer_id, resource_id, worker_id, service_variant_id, status, snapshot JSON)
schedules, waitlist_entries, queue_entries
payments, finance_entries

-- PLUGIN BEAUTY (extensão, não duplicação)
beauty_service_extensions (service_id, complexity, braid_count, ...)
beauty_booking_extensions (booking_id, reference_photos JSON)
```

**Plugin metadata JSON** evita colunas específicas no core:

```json
{
  "plugin": "beauty",
  "terminology": {"service_group": "Trança", "offering": "Modelo"},
  "ui": {"catalog_layout": "gallery", "max_photos": 6}
}
```

---

## 9. Eventos CoreFlow (padronizar)

| Evento CoreFlow | Evento atual | Status |
|-----------------|--------------|--------|
| `UserRegistered` | `identity.user.registered` | ✅ |
| `CompanyCreated` | `identity.company.created` | ✅ |
| `BookingCreated` | `reservation.created` | ✅ |
| `BookingApproved` | — | ❌ criar |
| `PaymentReceived` | — | ❌ criar |
| `CustomerCreated` | — | ❌ criar |

Namespace sugerido: `coreflow.{domain}.{action}` → facilita Kafka topics.

---

## 10. Produtos sobre CoreFlow

```
CoreFlow Engine (nunca vendido diretamente ao cliente final)
    │
    ├── BeautyOS      ← plugin beauty + branding (SEU MVP ATUAL)
    ├── SportsOS      ← plugin sports (quadras, árbitros)
    ├── ClinicOS      ← plugin clinic (consultórios, convênio)
    └── …
```

**Modelo de negócio:** CoreFlow = plataforma white-label; cada plugin = produto com pricing próprio.

---

## 11. Recomendação final

### Faça

1. **Rebrand arquitetural** para CoreFlow; BeautyOS vira plugin + produto  
2. **Formalize Sprint 0** — docs/, Docker, CI, ADR-001 (Metamodelo), Plugin Loader v0  
3. **Introduza metamodelo** com **aliases** — `/trancas` continua; `/v1/catalog/services` nasce em paralelo  
4. **Migre módulos** na ordem: identity ✅ → scheduling → booking → crm → finance  
5. **Preserve testes** — cada migração mantém suite verde  

### Não faça

1. Apagar SQLite, backups, DOCUMENTACAO.md  
2. Reescrever frontend antes do core API v1 estável  
3. Implementar Sports/Clinic antes do plugin loader + metamodelo  
4. Kafka/K8s no Sprint 0  

### Resposta direta

> *“Aproveitar o que já foi feito ou refazer tudo?”*

**Aproveitar ~70%.** Refazer apenas a **camada de modelagem** (metamodelo genérico + plugin config). A **lógica de negócio** (reserva, sinal, aprovação, fila, disponibilidade) é o ativo mais valioso — levaria meses para redescobrir em um rewrite limpo.

---

## 12. Próximo passo concreto

1. Criar `docs/00-VISION/Vision.md` + `docs/06-ADR/ADR001-metamodel.md`  
2. Implementar `core/plugin/PluginRegistry` (carrega manifest YAML por company)  
3. Definir entidades genéricas `Service`, `ServiceVariant`, `Booking` **ao lado** de `Tranca`/`Agendamento`  
4. ADR-002: BeautyOS como plugin oficial #1  

---

*CoreFlow Platform SAB — Análise estratégica · Julho 2026*
