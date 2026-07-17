# Sprint 9 — Order/Invoice + Workflow Editor + Enforcement Gradual

## Entregas

| Item | Status |
|------|--------|
| Tabela `core_orders` + sync agendamentos | ✅ |
| Tabela `core_invoices` + sync financeiro ENTRADA | ✅ |
| API GET `/v1/orders`, `/v1/invoices` | ✅ |
| Editor workflow proto (GET/PATCH `/v1/workflows/definitions`) | ✅ |
| `core_workflow_config` — override enabled por tenant | ✅ |
| Enforcement gradual `off` \| `warn` \| `block` | ✅ |
| Alembic `cf007_orders_invoices` | ✅ |

## Order / Invoice

- **Order:** snapshot comercial por reserva (`agendamentos` → `core_orders`)
- **Invoice:** entradas financeiras (`financeiro` ENTRADA → `core_invoices`)

## Workflow Editor (proto)

```bash
GET  /v1/workflows/definitions
PATCH /v1/workflows/definitions/{workflow_id}  {"enabled": false}
```

## Enforcement Gradual

```bash
CORE_ENFORCEMENT_MODE=warn make run   # headers, permite request
CORE_ENFORCEMENT_MODE=block make run  # HTTP 409 (booking legado only, ADR-033)
CORE_ENFORCEMENT_ENABLED=true         # legado → força block
```

## Próximo: CF-10

- Asset/Inventory metamodelo
- Marketplace plugin registry cloud
- Enforcement block em produção (staging)
