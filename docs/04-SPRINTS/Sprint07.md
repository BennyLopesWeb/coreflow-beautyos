# Sprint 7 — core_waitlist + BeautyAgent + Plugin SDK

## Entregas

| Item | Status |
|------|--------|
| Tabela `core_waitlist` + sync `fila` → v1 | ✅ |
| API GET `/v1/waitlist` | ✅ |
| BeautyAgent protótipo (`POST /v1/ai/analyze`) | ✅ |
| Manifest expandido (hooks, ai_capabilities, sdk) | ✅ |
| Alembic `cf005_waitlist` | ✅ |
| Sunset `/fila` → `/v1/waitlist` | ✅ |

## Manifest SDK (beauty v1.1.0)

Campos novos no `PluginManifest`:

- `api_version` — versão do schema de manifest
- `hooks` — mapa evento → handler
- `ai_capabilities` — capacidades IA declarativas
- `dependencies` — dependências semver da plataforma
- `sdk.routes` — rotas v1 expostas ao frontend

## BeautyAgent

Protótipo rule-based que delega ao `AgenteService` legado:

```bash
curl -X POST http://localhost:8000/v1/ai/analyze -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/v1/ai/tasks -H "Authorization: Bearer $TOKEN"
```

## Próximo: CF-8

- Workflow engine (aprovação, automações)
- AI Platform com LLM provider
- Enforcement core (escritas só `/v1`)
