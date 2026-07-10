# RFC-002 — Core Enforcement e Sunset Gradual de APIs Legado

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aprovado com ajustes (2026-07-09) |
| **Autor** | Principal Architect (CoreFlow) |
| **Data** | 2026-07-09 |
| **ADR relacionado** | [ADR-004](../adr/ADR-004-IncrementalEvolutionStrategy.md) |
| **Prioridade backlog** | Must Have — Release 1 |

---

## Objetivo

Ativar progressivamente `CoreEnforcementMiddleware` e `LegacySunsetMiddleware` para migrar escritas do legado para `/v1/*`, **sem quebrar** clientes existentes.

## Problema

Três camadas API coexistem (`backend/app/main.py`):

| Camada | Exemplos | Consumidores |
|--------|----------|--------------|
| Legado PT-BR | `/agenda`, `/trancas`, `/clientes` | Frontend admin, fluxos antigos |
| BeautyOS | `/reservations`, `/payments`, `/queue` | Frontend parcial |
| CoreFlow v1 | `/v1/bookings`, `/v1/catalogs`, … | SDK, testes CF, migração |

Regras de negócio críticas ainda em `app/services/` — commands CQRS delegam ao legado (`booking/application/commands/`).

## Motivação

- **API First:** uma superfície canônica `/v1/*`
- Reduzir divergência de regras entre legado e core
- Preparar frontend para consumir apenas `@coreflow/sdk`

## Alternativas

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Enforcement gradual warn → block por rota | **Preferida** |
| B | Desligar legado de uma vez | Rejeitada — quebra compatibilidade |
| C | Manter legado indefinidamente | Rejeitada — dívida permanente |

## Impacto

### Fase 1 (baixo risco) — após aprovação

- Documentar mapa rota legado → v1
- Adicionar headers `Deprecation` / `Sunset` (já parcial em `LegacySunsetMiddleware`)
- Métricas: contagem de hits por rota legado

### Fase 2

- `CORE_ENFORCEMENT_MODE=warn` em staging — log quando write legado duplicaria v1

### Fase 3

- Migrar **um** fluxo frontend (ex.: listagem bookings admin) para SDK v1

### Fase 4

- `CORE_ENFORCEMENT_MODE=block` para rotas com paridade v1 completa

## Compatibilidade

- Leituras legado mantidas até frontend migrado
- Escritas bloqueadas **somente** quando v1 equivalente testado
- Rollback: `CORE_ENFORCEMENT_MODE=off`

---

## Requisitos adicionais (aprovação condicional)

### 1. Anti-Corruption Layer (ACL)

Toda integração Core ↔ Legado **deve** passar por ACL. **Proibido** import direto de `app/services/` em módulos core (meta alvo).

```
Legacy Domain (Agendamento)
        ↓
Legacy Adapter (ACL)
        ↓
Booking Port (interface)
        ↓
Core Booking Module
```

Implementação: `backend/app/shared/acl/` — ports + adapters. Migração incremental; delegação existente encapsulada em fases futuras.

### 2. Feature Flags

Toda migração protegida por flags (settings + `FeatureFlagService`):

| Flag | Setting | Default |
|------|---------|---------|
| `booking.core.enabled` | `FEATURE_BOOKING_CORE_ENABLED` | `false` |
| `ai.core.enabled` | `FEATURE_AI_CORE_ENABLED` | `false` |
| `workflow.enabled` | `FEATURE_WORKFLOW_ENABLED` | `true` |
| `plugin.engine.enabled` | `FEATURE_PLUGIN_ENGINE_ENABLED` | `true` |

API: `GET /v1/platform/feature-flags`

### 3. Telemetria (pré-sunset)

Antes de remover qualquer rota legado, registrar:

- **Utilização** — hits por layer/path (Prometheus)
- **Performance** — latência por layer
- **Erros** — 4xx/5xx por layer
- **Usuários impactados** — tenant/company quando autenticado

Métricas: `coreflow_http_requests_total`, `coreflow_http_request_duration_seconds`  
Mapa: `GET /v1/platform/legacy-route-map`

---

## Plano de Migração

Ver fases acima. Cada fase: PR isolado + testes + doc sprint.

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Frontend quebra | Migrar tela a tela; feature flag |
| Regras divergentes v1 vs legado | Testes de paridade antes de block |
| Operadores dependem de `/admin` legado | Manter read-only legado até Release 2 |

## Rollback

`settings.CORE_ENFORCEMENT_MODE=off` e `LEGACY_SUNSET_ENABLED=false` em `backend/app/core/config.py`.

## Arquivos afetados (estimativa por fase)

| Fase | Arquivos |
|------|----------|
| 1 | `core/legacy_sunset.py`, `core/core_enforcement.py`, docs |
| 2 | `main.py`, middleware config |
| 3 | `frontend/src/services/*.ts` |
| 4 | `core/core_enforcement.py` route map |

## Estimativa

| Fase | Esforço | Risco |
|------|---------|-------|
| 1 | 2–4 h | Baixo |
| 2 | 4 h | Baixo |
| 3 | 8–16 h | Médio |
| 4 | 4 h | Médio |

---

**Aguardando aprovação. Nenhuma fase implementada nesta entrega.**
