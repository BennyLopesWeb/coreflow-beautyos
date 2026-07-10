# ADR-006 — Plugin Architecture

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2026-07-09 |

## Contexto

CoreFlow deve permitir novos produtos via plugins sem alterar core. Loader e manifests existem (`backend/plugins/`, `core/plugin/`).

## Problema

Faltam definições formais de lifecycle, dependencies, context e extensibilidade.

## Decisão

### Componentes do Plugin Engine

| Componente | Responsabilidade | Implementação atual |
|------------|------------------|---------------------|
| **Manifest** | Declarativo: id, terminology, features, hooks, mobile, sdk | `manifest.yaml` + `PluginManifest` Pydantic |
| **Registry** | Catálogo em memória de plugins carregados | `plugin_registry` singleton |
| **Loader** | Parse YAML, validação schema, load no startup | `PluginRegistry.load_all()` |
| **Lifecycle** | registered → loaded → active (per tenant futuro) | loaded only; tenant install 🔜 |
| **Dependencies** | `dependencies:` no manifest (semver platform) | Declarado, não enforced runtime |
| **Plugin Context** | Runtime: plugin_id, company, manifest, permissions | 🔜 `PluginContext` dataclass |
| **Plugin Events** | Hooks: `booking.created` → module path | Declarado em manifest |
| **Plugin Permissions** | Capabilities por plugin | 🔜 manifest extension |
| **Plugin Dashboard / Menus** | UI config por plugin | 🔜 manifest extension |
| **Plugin SDK** | Geradores CLI | 🔜 Release 4 |

### Regras

1. Plugin **nunca** importa de `app/services/` legado
2. Core **nunca** importa código em `plugins/{id}/` exceto via registry/hooks declarados
3. Terminologia via `manifest.terminology` — API retorna labels por plugin
4. Feature flag `plugin.engine.enabled` controla registry no startup (default true)
5. Novo plugin = novo `manifest.yaml` + testes registry — **sem** alterar core

### Lifecycle (alvo)

```
discovered → validated → loaded → enabled(company) → disabled → deprecated
```

Estado atual: `loaded` após startup.

## Consequências

- clinic/sports permanecem manifest-only até domínio dedicado
- Plugin Context implementado em fase futura (Backlog EPIC-PLG-001)

## Benefícios

- Build Once. Configure Everywhere.
- Novos verticais sem deploy core

## Trade-offs

- Sem isolamento de processo/classloader (Python monolith)

## Alternativas descartadas

- Plugin como microsserviço separado — prematuro (ADR modular monolith)

## Referências

- `backend/app/core/plugin/manifest.py`
- `backend/plugins/beauty/manifest.yaml`
- ADR-002 beauty plugin (legado `docs/06-ADR/ADR002-beauty-plugin.md`)
