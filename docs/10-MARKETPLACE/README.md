# 10 — Marketplace

> Sprint CF-10 ✅ (proto cloud)

## Visão

Marketplace de plugins CoreFlow: publicação, instalação por tenant, billing e reviews.

## Implementado (CF-10)

| Item | Status |
|------|--------|
| Catálogo cloud `backend/marketplace/catalog.yaml` | ✅ |
| API `GET /v1/marketplace/listings` | ✅ |
| API `POST /v1/marketplace/install` | ✅ |
| Instalação via `company.plugin_id` | ✅ |
| Loader local `backend/plugins/` | ✅ |

## Catálogo

- **beauty** — instalável, local, free
- **sports** — preview marketplace, não instalável ainda
- **clinic** — preview marketplace, paid

## Próximo

- Registry cloud remoto (`MARKETPLACE_CATALOG_URL`)
- Billing e reviews
- Publicação de plugins third-party
