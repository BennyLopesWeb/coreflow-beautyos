# 06 — Plugin Framework

Extensões estilo VSCode — plugins especializam CoreFlow sem alterar o núcleo.

## Manifest atual (`manifest.yaml`)

```yaml
plugin_id: beauty
terminology: { worker: Profissional, resource: Cadeira, ... }
features: [deposit_payment, waitlist, ...]
metamodel_mappings: { catalog: Tranca, offering: ServiceImage, ... }
```

## Manifest alvo (SDK)

| Seção | Status | Descrição |
|-------|--------|-----------|
| `plugin.name/version` | ✅ | Identidade |
| `terminology` | ✅ | Rótulos UI |
| `metamodel_mappings` | ⚠️ | Expandir Asset, Inventory |
| `menus` | 🔜 | Navegação admin |
| `permissions` | 🔜 | RBAC por plugin |
| `entities` | 🔜 | Schema extensível |
| `routes` | 🔜 | Registro dinâmico FastAPI |
| `dashboard` | 🔜 | Widgets |
| `reports` | 🔜 | Relatórios |
| `ai` | 🔜 | Agents declarativos |
| `events` | 🔜 | subscribe/publish |

## Código

- `backend/app/core/plugin/registry.py`
- `backend/plugins/beauty/manifest.yaml`
- API: `GET /v1/plugins`, `GET /v1/plugins/config/by-company/{slug}`

Ver [`03-PLUGINS/Beauty.md`](../03-PLUGINS/Beauty.md)
