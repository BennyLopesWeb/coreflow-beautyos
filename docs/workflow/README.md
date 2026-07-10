# Workflow Engine

Automações event-driven desacopladas.

| Recurso | Local |
|---------|-------|
| Engine | `backend/app/modules/workflow/engine/workflow_engine.py` |
| Definições YAML | `backend/workflows/` |
| Handlers | `backend/app/modules/workflow/application/handlers.py` |
| API | `/v1/workflows` |

## Fluxo alvo

```
BookingCreated → PaymentConfirmed → WhatsApp → Invoice → CRM → NotifyWorker
```

Cada passo via eventos + workflow steps — sem acoplamento direto entre módulos.

## Evolução

- Editor visual (future)
- Catálogo de triggers/actions padronizado
- Permissões por plugin
