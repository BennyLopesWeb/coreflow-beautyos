# CoreFlow — Mobile Platform

**Documento:** `docs/MobilePlatform.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Estratégico — BFF, SDK-first, offline  
**Stack atual:** Expo ~50, `@coreflow/sdk`, EAS DevOps ✅

---

## Mudança de visão

### Antes (implicit)

```
Backend API → Frontend React monolith → App Expo
```

### Alvo (Platform-as-a-Product)

```mermaid
flowchart TB
    CORE[Core API /v1/*]
    BFF[BFF Layer]
    SDK[@coreflow/sdk]
    WEB[Web Admin]
    MOB[Mobile App]
    PART[Partners / Integrators]
    MKT[Marketplace Apps]

    CORE --> BFF
    CORE --> SDK
    BFF --> WEB
    BFF --> MOB
    SDK --> MOB
    SDK --> WEB
    SDK --> PART
    SDK --> MKT
```

**SDK é cidadão de primeira classe** — BFF agrega para UX; SDK é contrato estável.

---

## Camadas

### 1. Core API

- `/v1/*` — regra de negócio, OpenAPI, versionada
- Documentada em `APIGovernance.md`
- Nunca expor legado a clientes novos

### 2. BFF (Backend for Frontend)

| BFF | Audiência | Responsabilidade | Release |
|-----|-----------|------------------|---------|
| `bff-mobile` | App Expo | Agregação screens, payload shaping, offline queue API | R3 |
| `bff-admin` | Web admin | Dashboards, bulk ops | R4 |
| `bff-public` | Partners | Rate-limited subset | R6 |

**Regra:** BFF **não** contém regra de negócio — orquestra Core API calls.

Implementação: routers FastAPI `routers/bff/` ou module `modules/bff/` — same monolith initially.

### 3. SDK (`@coreflow/sdk`)

| Responsabilidade | Detalhe |
|------------------|---------|
| HTTP client tipado | OpenAPI codegen R6 |
| Auth token refresh | JWT |
| Terminology resolver | Plugin config API |
| Offline queue client | R4 |
| Realtime subscriptions | R4 |
| Error mapping | Problem Details |

Packages:

- `@coreflow/sdk` — core ✅
- `@coreflow/sdk-mobile` — offline, push helpers 🔜
- `@coreflow/plugin-beauty` — vertical types 🔜

### 4. Web & Mobile

- **Mobile:** Expo primary — profissional em campo
- **Web:** Expo web + admin denso
- Shared: SDK + design tokens from TCE theme

---

## Mobile Offline First

### Por quê

Quadras, eventos, feiras — conectividade instável. Staff deve operar sem interrupção.

### Escopo offline (R4)

| Operação | Offline | Sync conflict |
|----------|---------|---------------|
| Check-in booking | ✅ | last-write-wins + audit |
| View agenda | ✅ read cache | refresh on connect |
| Register payment (cash) | ✅ queue | idempotency key |
| Consumption/order | ✅ queue | merge |
| Inventory adjustment | ✅ queue | server validate |
| Create booking | ⚠️ queue | availability revalidate |
| Approve booking | ❌ online | requires payment state |

### Arquitetura offline

```mermaid
flowchart LR
    APP[Mobile App]
    LDB[(SQLite/WatermelonDB)]
    OQ[Offline Queue]
    SDK[@coreflow/sdk]
    BFF[bff-mobile]
    CORE[Core API]

    APP --> LDB
    APP --> OQ
    OQ --> SDK
    SDK --> BFF
    BFF --> CORE
    CORE -->|sync response| OQ
```

| Componente | Tecnologia |
|------------|------------|
| Local DB | WatermelonDB or Expo SQLite |
| Queue | Outbox pattern client-side |
| Sync | Pull delta `/bff-mobile/sync?since=timestamp` |
| Conflict UI | Staff resolves conflicts |

### Feature flag

`FEATURE_MOBILE_OFFLINE_ENABLED` — default false · R4 spike R4 production R5

---

## Deep links & universal links

✅ Implementado CF-12+ — manifest `sdk.deep_links` per plugin.

---

## Push & notifications

Expo Push ✅ — integrar `RealtimePlatform.md` for in-app.

---

## White-label mobile

EAS whitelabel ✅ — per plugin manifest `mobile:` block.

---

## Roadmap

| Release | Entrega |
|---------|---------|
| R2 | SDK bookings tab migration |
| R3 | BFF mobile spike, terminology 100% dynamic |
| R4 | Offline queue MVP, SDK codegen |
| R5 | Offline production, conflict UI |
| R6 | `@coreflow/sdk-mobile` package |
| R7 | Flutter optional adapter |

---

## Referências

- `docs/RealtimePlatform.md`
- `docs/DeveloperExperience.md`
- `docs/TenantCustomizationEngine.md`
- `modules/mobile/` — EAS DevOps
- `packages/coreflow-sdk/`
