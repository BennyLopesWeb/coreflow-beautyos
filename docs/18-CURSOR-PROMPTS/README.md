# 18 — Cursor Prompts

> Stub SAB — prompts reutilizáveis para evolução CoreFlow

## Sprint continuation

```
Prossiga com CF-N conforme docs/04-SPRINTS/Sprint0N.md.
Valide pytest completo. Atualize DOCUMENTACAO.md e docs/README.md.
Não reescreva legado — Strangler Fig via sync services.
```

## Novo conceito metamodelo

```
Adicione CoreConcept X seguindo padrão de core_customers:
- domain/models.py
- application/legacy_sync_service.py
- application/*_query_service.py
- routers/v1_*.py
- alembic cf00N_*
- testes test_cfN_*.py
```

## Plugin novo

```
Crie backend/plugins/{id}/manifest.yaml com terminology, features,
metamodel_mappings, sdk.routes. Registre via PluginRegistry.
```
