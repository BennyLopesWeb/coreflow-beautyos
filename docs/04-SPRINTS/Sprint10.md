# Sprint 10 — Asset/Inventory + Marketplace + Staging Enforcement

## Entregas

| Item | Status |
|------|--------|
| Tabela legado `inventory_items` + seed demo | ✅ |
| `core_assets` + `core_inventory` + sync | ✅ |
| API GET `/v1/assets`, `/v1/inventory` | ✅ |
| Marketplace cloud proto (`catalog.yaml`) | ✅ |
| API GET `/v1/marketplace/listings` + POST `/install` | ✅ |
| `APP_ENV=staging` → enforcement `block` default | ✅ |
| Alembic `cf008_assets_inventory` | ✅ |

## Asset / Inventory

- **Asset:** definição do insumo (`inventory_items` → `core_assets`)
- **Inventory:** quantidade em estoque (`core_inventory`)
- Seed demo: cabelo sintético, gel, pente (bootstrap)

## Marketplace

```bash
GET  /v1/marketplace/listings
POST /v1/marketplace/install  {"plugin_id": "beauty"}
```

Catálogo: `backend/marketplace/catalog.yaml` (beauty local + sports/clinic preview).

## Staging Enforcement

```bash
APP_ENV=staging make run          # block legado writes por default
CORE_ENFORCEMENT_MODE=warn ...    # override explícito
CORE_ENFORCEMENT_MODE=off ...     # desliga mesmo em staging
```

## Próximo: CF-11

- Mobile SDK TypeScript package
- Plugin sports/clinic manifests locais
- Production enforcement rollout
