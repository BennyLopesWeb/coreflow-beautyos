# BeautyOS — Arquitetura v3.0

**Modular Monolith · DDD · Hexagonal · API First · Event-Driven**

| | |
|---|---|
| **Versão** | 3.0 |
| **Autor** | Benigno Fernandes Lopes |
| **Status** | Fase A — multi-tenant implementado; reestruturação modular em andamento |

Documentos relacionados: `BEAUTYOS_BLUEPRINT.md` · `BEAUTYOS_MIGRATION.md` · `DOCUMENTACAO.md`

---

## 1. Decisão arquitetural

O BeautyOS adota **Monólito Modular** como arquitetura inicial.

| Abordagem | Por quê |
|-----------|---------|
| **Modular Monolith** | Velocidade no MVP, um deploy, debug simples |
| **Não microserviços agora** | Complexidade operacional prematura (K8s, rede, observabilidade distribuída) |
| **Preparado para extração** | Módulos desacoplados por portas, eventos e contratos → extração gradual |

Módulos candidatos à extração futura (ordem provável):

1. **Notifications** (WhatsApp, push, e-mail)
2. **AI Platform** (LLM, Vision, MCP)
3. **Marketplace** (busca, geo, reviews)
4. **Analytics** (KPIs, dashboards, batch)

---

## 2. Pilares da arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        BEAUTYOS v3.0                            │
├─────────────────────────────────────────────────────────────────┤
│  DDD          Modelar domínio de negócio com linguagem ubíqua   │
│  Hexagonal    Núcleo isolado; tecnologia nas bordas (adapters)│
│  API First    Funcionalidade existe na API antes de qualquer UI │
│  Event-Driven Comunicação desacoplada entre módulos             │
│  Modular      Monólito organizado por bounded contexts          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 Domain-Driven Design (DDD)

Cada módulo possui:

| Camada | Responsabilidade | Exemplo (Booking) |
|--------|------------------|-------------------|
| **Domain** | Entidades, value objects, regras, eventos de domínio | `Reservation`, `ReservationStatus`, `ReservationCreated` |
| **Application** | Casos de uso, orquestração, ports | `CreateReservationUseCase`, `ReservationRepositoryPort` |
| **Infrastructure** | Adapters: SQLAlchemy, Redis, filas | `SqlAlchemyReservationRepository` |
| **API** | HTTP routers, DTOs de entrada/saída | `POST /v1/bookings` |

**Bounded contexts** (módulos de negócio):

```
identity/       authentication, users, companies, RBAC
catalog/        categories, offerings (ex-trancas/modelos)
scheduling/     availability, agenda_dia, blocks
booking/        reservations, waitlist, operational queue
payments/       PIX, deposits, refunds, providers
crm/            customers, profiles, photos, tags
finance/        ledger, cash flow, commissions
marketing/      campaigns, coupons, loyalty
marketplace/    public profiles, search, reviews
notifications/  WhatsApp, push, e-mail
ai/             assistant, vision, tools, MCP
analytics/      KPIs, dashboards
files/          uploads, S3/MinIO
settings/       company config, segments
audit/          audit trail
```

### 2.2 Arquitetura Hexagonal (Ports & Adapters)

```
                    ┌──────────────────────────────────┐
  HTTP (FastAPI) ──►│           API Adapters           │
  WhatsApp      ──►│                                  │
  Flutter/Web   ──►│         APPLICATION              │
                    │    (Use Cases / Services)        │
  Celery Jobs   ──►│                                  │
                    │           DOMAIN                 │
                    │  (Entities, Rules, Events)       │
                    └───────────┬──────────────────────┘
                                │ Ports (interfaces)
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
         MySQL Repo        Redis Cache      Payment Provider
         (adapter)         (adapter)        (Mercado Pago…)
              │                 │                 │
              └─────────────────┴─────────────────┘
                         Infrastructure
```

**Regra:** o **domain** e **application** não importam FastAPI, SQLAlchemy nem HTTP.

**Ports** (interfaces Python / Protocol):

```python
# application/ports/payment_provider.py
class PaymentProviderPort(Protocol):
    def create_pix_charge(self, amount: Decimal, reference: str) -> PixCharge: ...
```

**Adapters** (implementações):

```python
# infrastructure/payments/mercadopago_adapter.py
class MercadoPagoAdapter(PaymentProviderPort): ...
# infrastructure/payments/mock_pix_adapter.py  ← Fase 0
class MockPixAdapter(PaymentProviderPort): ...
```

### 2.3 API First

- Toda funcionalidade nasce como **endpoint + contrato OpenAPI**.
- Frontends (React, Flutter, WhatsApp bot) são **clientes finos**.
- Testes de contrato validam que a API cumpre o blueprint antes da UI.

Versionamento: `/v1/` → evolução sem breaking changes abruptos.

### 2.4 Event-Driven Architecture

Módulos comunicam-se por **eventos de domínio**, não por imports diretos entre services quando possível.

```
 booking                payments              notifications
   │                       │                       │
   │ ReservationCreated    │                       │
   ├──────────────────────►│ (handler)             │
   │                       │ PaymentRequested      │
   │                       ├──────────────────────►│ WhatsApp notify
   │                       │                       │
   │ ReservationApproved   │                       │
   ├──────────────────────────────────────────────►│ Push + WhatsApp
```

**Fase atual:** `InMemoryEventBus` (síncrono, mesmo processo).  
**Fase B:** RabbitMQ / Redis Streams.  
**Fase C:** Kafka para analytics e replay.

| Evento | Publicado por | Consumidores |
|--------|---------------|--------------|
| `ReservationCreated` | booking | notifications, finance, ai |
| `DepositConfirmed` | payments | booking, notifications, finance |
| `ReservationApproved` | booking | scheduling, notifications, calendar |
| `CustomerInactiveDetected` | crm / ai | marketing, notifications |

Implementação base: `app/shared/events/`.

### 2.5 Modular Monolith — estrutura de pastas alvo

```
backend/app/
├── main.py                    # Composição: registra routers dos módulos
├── shared/
│   ├── kernel/                # TenantContext, RBAC, exceptions
│   ├── events/                # DomainEvent, EventBus, handlers registry
│   └── contracts/             # DTOs compartilhados entre módulos
├── modules/
│   ├── identity/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/router.py
│   ├── catalog/
│   ├── booking/
│   ├── payments/
│   └── …
└── legacy/                    # Código Fase 0 (Strangler Fig — removido gradualmente)
    ├── models/
    ├── services/
    └── routers/
```

**Strangler Fig:** código atual em `models/`, `services/`, `routers/` migra módulo a módulo. Routers legados permanecem até paridade na API `/v1/`.

---

## 3. Mapa: código atual → módulos v3.0

| Módulo alvo | Código Fase 0/A | Cobertura |
|-------------|-----------------|-----------|
| **identity** | `modules/identity/` | ~95% ✅ |
| **catalog** | `Tranca`, `ServiceImage`, `tranca_service` | ~70% |
| **scheduling** | `AgendaDia`, `DisponibilidadeService`, `Schedule` | ~65% |
| **booking** | `Agendamento`, `ReservationService`, `Fila`, `QueueEntry` | ~75% |
| **payments** | `Payment`, `PaymentReservationService`, `integrations/pix` | ~40% |
| **crm** | `Cliente`, `admin_service` CRM | ~30% |
| **finance** | `Financeiro`, `FinanceiroService` | ~25% |
| **notifications** | `NotificationService`, `integrations/whatsapp` | ~25% |
| **ai** | `AgenteService`, `AgentTask` | ~10% |

**Dívida técnica principal:** services importam outros services diretamente (acoplamento). Eventos reduzem isso progressivamente.

---

## 4. Fluxo de uma requisição (hexagonal)

Exemplo: **criar reserva**

```
1. API Adapter     POST /reservations  → ReservationCreate DTO
2. Application     CreateReservationUseCase.execute(dto, tenant)
3. Domain          Reservation.validate(); emit ReservationCreated
4. Infrastructure  SqlAlchemyReservationRepository.save()
5. Event Bus       ReservationCreated → handlers (notification, payment pending)
6. API Adapter     ReservationResponse DTO
```

---

## 5. Multi-tenant + modular

Todo módulo recebe `TenantContext` (`company_id`, `role`) nos casos de uso.

```python
class CreateReservationUseCase:
    def execute(self, cmd: CreateReservationCommand, tenant: TenantContext) -> Reservation:
        ...
```

Isolamento enforced na **application layer** (não só no router).

---

## 6. Roadmap de reestruturação (sem big bang)

| Fase | Entrega | Prazo estimado |
|------|---------|----------------|
| **A** ✅ | Company, RBAC, JWT tenant, EventBus, **módulo identity** | Concluído |
| **B1** ✅ | Extrair `identity/` (ports, adapters, API) | Concluído |
| **B2** 🔜 | Extrair `booking/` + eventos Reservation* | Próximo |
| **B2** | Extrair `booking` + eventos Reservation* | 2–3 sem |
| **B3** | Extrair `payments` + port PixProvider | 1–2 sem |
| **B4** | RabbitMQ + handlers assíncronos | 2 sem |
| **C** | `/v1/` API consolidada; deprecar legacy | 2 sem |
| **D** | MySQL + Alembic; Redis cache | 2–3 sem |

---

## 7. Critérios para extrair um microsserviço

Só extrair quando **todos** forem verdadeiros:

1. Módulo com **contratos estáveis** (API + eventos versionados)
2. **Zero imports** diretos de outros módulos (só eventos/API)
3. Necessidade de **escala independente** (ex.: IA consome muita GPU)
4. Time/infra preparados para deploy, monitoramento e CI separados

---

## 8. Stack alinhada à arquitetura

| Camada | Tecnologia | Papel |
|--------|------------|-------|
| API | FastAPI | Driving adapter HTTP |
| Domain | Python puro | Entidades e regras |
| ORM | SQLAlchemy 2.x | Driven adapter persistência |
| Events (MVP) | In-memory bus | Desacoplamento local |
| Events (prod) | RabbitMQ → Kafka | Assíncrono, replay |
| Cache | Redis | Slots, sessões |
| Jobs | Celery | Handlers de eventos pesados |
| DB | MySQL | Multi-tenant |

---

## 9. Princípios de implementação

1. **Regra de negócio no domain/application** — nunca no router ou no React/Flutter.
2. **Um bounded context = um módulo** — sem `service` genérico que faz tudo.
3. **Evento > import** — preferir publicar `ReservationApproved` a chamar `NotificationService` diretamente (transição gradual).
4. **Ports para toda integração externa** — Pix, WhatsApp, Google Calendar, OpenAI.
5. **Testes por camada** — domain (unit), application (mock ports), API (integration).

---

*BeautyOS Architecture v3.0 — Benigno Fernandes Lopes*
