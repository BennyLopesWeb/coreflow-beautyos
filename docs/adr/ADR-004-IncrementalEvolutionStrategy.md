# ADR-004 — Estratégia de Evolução Incremental (Strangler Fig)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-002](../rfc/RFC-002-CoreEnforcementSunset.md) |

## Contexto

O repositório contém camada legada (`app/services/`, `app/models/`) e camada CoreFlow v1 (`app/modules/`, `/v1/*`) sincronizadas via `legacy_sync_service.py` e commands CQRS que delegam ao legado.

ADR-001 estabeleceu metamodelo genérico. CF-1→CF-25 implementaram entidades `core_*`, eventos, plugins, mobile DevOps.

## Problema

Big-bang migration quebraria:

- Frontend Expo (`frontend/src/services/` — 12 services legados)
- Operadores usando `/agenda`, `/trancas`
- Regras de negócio validadas em produção piloto

## Decisão

Manter **Strangler Fig** como estratégia oficial:

1. **Core genérico** recebe novas features via `/v1/*` + modules
2. **Legado** permanece read/write até paridade testada
3. **Sync bidirecional** via legacy_sync enquanto necessário
4. **Enforcement** progride: `off` → `warn` → `block` por rota (`core/core_enforcement.py`)
5. **Sunset** HTTP headers em rotas legado (`core/legacy_sunset.py`)
6. **Plugins** especializam terminologia; core nunca importa `Tranca`, `Agendamento`

Proibido:

- Mover centenas de arquivos de uma vez
- Alterar regras de negócio existentes sem testes de paridade
- Remover routers legado antes de Release 2 (roadmap)

### Rollback documentado (obrigatório)

Toda evolução arquitetural **deve** documentar rollback:

| Mecanismo | Uso |
|-----------|-----|
| Feature flags | Desligar path novo (`FEATURE_*_ENABLED=false`) |
| `CORE_ENFORCEMENT_MODE=off` | Restaurar escritas legado |
| `LEGACY_SUNSET_ENABLED=false` | Remover headers sunset |
| Alembic downgrade | Reversão schema (quando aplicável) |
| Git revert | PR de fase isolada — uma fase = um revert |

Cada sprint doc deve incluir seção **Rollback** com comandos/settings exatos.

## Consequências

- Período de dual-write/dual-read prolongado
- Commands booking continuam delegando até Fase dedicada (Backlog EPIC-CORE-003)
- SchedulingEngine mantém `LegacySchedulingAdapter` temporariamente

## Benefícios

- Zero downtime conceitual para piloto beauty
- Novos verticais (clinic, sports) usam v1 desde o início
- Rollback trivial via settings

## Trade-offs

| Pró | Contra |
|-----|--------|
| Baixo risco | Complexidade cognitiva (3 APIs) |
| Compatibilidade | Duplicação temporária de lógica |

## Alternativas descartadas

| Alternativa | Motivo |
|-------------|--------|
| Rewrite v2 greenfield | Custo, risco, perda de regras validadas |
| Congelar legado sem v1 | Impede plataforma genérica |
| Microsserviços por módulo | Prematuro; Modular Monolith suficiente |

## Referências

- `docs/ArchitectureAssessment.md` §3, §23, §26 RF-01..RF-03
- `docs/06-ADR/ADR001-metamodel.md`
- `backend/app/core/core_enforcement.py`
- `docs/rfc/RFC-002-CoreEnforcementSunset.md`
