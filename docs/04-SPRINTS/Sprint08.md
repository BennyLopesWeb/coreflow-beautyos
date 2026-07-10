# Sprint 8 — Workflow Engine + AI Platform + Core Enforcement

## Entregas

| Item | Status |
|------|--------|
| Workflow Engine (YAML → event handlers) | ✅ |
| Tabela `core_workflow_runs` + auditoria | ✅ |
| `POST /v1/bookings/{id}/approve` + `/reject` | ✅ |
| Eventos `booking.approved` / `booking.rejected` | ✅ |
| AI Platform LLM providers (mock + OpenAI) | ✅ |
| Core Enforcement middleware (opt-in) | ✅ |
| Alembic `cf006_workflow_runs` | ✅ |

## Workflow YAML

Definições em `backend/workflows/*.yaml`:

```yaml
workflow_id: beauty_deposit_to_approval
trigger: payment.deposit.confirmed
steps:
  - action: notify_admin
  - action: log
```

Carregados no startup via `register_workflow_handlers()`.

## AI Platform

```bash
# Mock (default)
AI_LLM_ENABLED=false

# OpenAI (opcional)
AI_LLM_ENABLED=true AI_LLM_PROVIDER=openai OPENAI_API_KEY=sk-...
```

Providers: `MockLLMProvider`, `OpenAILLMProvider` (fallback mock).

## Core Enforcement

```bash
CORE_ENFORCEMENT_ENABLED=true make run
```

Bloqueia POST/PUT/PATCH/DELETE em rotas legado com sucessor v1 (403 + header `Link`).

## Próximo: CF-9

- Order/Invoice metamodelo
- Workflow visual editor (admin)
- Enforcement gradual em produção
