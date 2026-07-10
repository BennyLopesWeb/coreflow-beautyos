# 19 — Architecture Decision Records

> ADRs CoreFlow Platform (renumerar de `06-ADR/`)

## Índice

| ADR | Título | Status |
|-----|--------|--------|
| [ADR-001](../06-ADR/ADR001-metamodel.md) | Metamodelo universal + Strangler Fig | Aceito |
| [ADR-002](./ADR002-plugin-manifest-sdk.md) | Manifest expandido + SDK routes | Aceito (CF-7) |

## ADR-002 — Plugin Manifest SDK (CF-7)

**Contexto:** Plugins precisam declarar capacidades IA, hooks e rotas v1 para frontends genéricos.

**Decisão:** Estender `PluginManifest` com `api_version`, `hooks`, `ai_capabilities`, `dependencies`, `sdk`.

**Consequências:**

- Frontends leem `sdk.routes` em vez de hardcode
- BeautyAgent usa `ai_capabilities` para habilitar automações
- Compatibilidade verificável via `dependencies` / `min_platform_version`
