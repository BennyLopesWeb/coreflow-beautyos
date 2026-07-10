# CoreFlow — API Governance

**Documento:** `docs/APIGovernance.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Normativo — padrões API First  
**Base:** OpenAPI 3.x em `/docs`

---

## Propósito

Evitar divergência entre módulos, plugins e clientes. Toda API pública `/v1/*` obedece este documento.

---

## Naming conventions

| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| Paths | kebab-case, plural nouns | `/v1/bookings`, `/v1/customers` |
| Path params | snake_case | `{booking_id}` |
| Query params | snake_case | `?company_id=1&page=2` |
| JSON fields | snake_case | `scheduled_at`, `customer_id` |
| Event types | dot notation | `booking.created` |
| Headers | `X-CoreFlow-*` custom | `X-CoreFlow-Layer` |

**Proibido em API core:** `tranca_id`, `agendamento` — usar Meta Model.

---

## DTO & Request/Response

| Regra | Detalhe |
|-------|---------|
| Framework | Pydantic v2 models |
| Request | `*Create`, `*Update`, `*Query` suffix |
| Response | `*Response` — nunca expor ORM |
| Lists | `{ "items": [], "total": N, "page": P, "page_size": S }` |
| IDs | integer internal; UUID 🔜 public API |
| Timestamps | ISO 8601 UTC `2026-07-09T15:00:00Z` |
| Money | integer cents + `currency` code (🔜 R5) |
| Null vs omit | Optional absent = null accepted on PATCH |

---

## Pagination

```json
GET /v1/bookings?page=1&page_size=20&sort=-scheduled_at

{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20,
  "has_next": true
}
```

| Param | Default | Max |
|-------|---------|-----|
| `page` | 1 | — |
| `page_size` | 20 | 100 |
| `sort` | `-created_at` | whitelist fields |

Cursor pagination 🔜 public API high-volume (R6).

---

## Errors — Problem Details (RFC 7807)

```json
{
  "type": "https://coreflow.app/errors/booking-slot-unavailable",
  "title": "Slot unavailable",
  "status": 409,
  "detail": "Resource 5 has no availability at 2026-07-10T10:00:00Z",
  "instance": "/v1/bookings",
  "errors": [
    {"field": "scheduled_at", "code": "slot_unavailable", "message": "..."}
  ],
  "correlation_id": "req-abc-123"
}
```

| Status | Uso |
|--------|-----|
| 400 | Validation |
| 401 | Unauthenticated |
| 403 | Forbidden / tenant |
| 404 | Not found |
| 409 | Conflict (booking, resource) |
| 422 | Business rule violation |
| 429 | Rate limit |
| 500 | Internal (never leak stack) |

---

## Idempotency

| Escopo | Header | Retention |
|--------|--------|-----------|
| POST create | `Idempotency-Key: uuid` | 24h |
| Payments | Obrigatório | 72h |
| Webhooks inbound | `X-Idempotency-Key` | 7d |

Store: `idempotency_keys` table tenant-scoped.

---

## Rate limiting (🔜 R3 public, R6 full)

| Tier | Requests/min | Burst |
|------|--------------|-------|
| Free | 60 | 10 |
| Pro | 600 | 100 |
| Enterprise | Custom | Custom |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.

---

## OpenAPI

| Requisito | Detalhe |
|-----------|---------|
| Auto-gen | FastAPI `/docs`, `/openapi.json` |
| Export CI | `openapi.json` committed per release |
| Breaking check | oasdiff in fitness functions |
| Tags | Match Domain Registry names |
| Examples | Required for public endpoints R6 |
| Security scheme | Bearer JWT documented |

---

## Multi-tenant

- JWT claim `company_id` authoritative
- Never accept `company_id` from body without superuser
- Filter all queries by tenant
- Cross-tenant = 403 + audit log

---

## Plugin API extensions

Plugins **não** criam `/v1/*` routes no core — usam:

1. Core APIs existentes
2. Plugin hooks (events)
3. Future: `/v1/plugins/{id}/extensions/*` namespace (R5)

---

## Review checklist (PR)

- [ ] OpenAPI updated
- [ ] Problem Details format
- [ ] Pagination on lists
- [ ] snake_case fields
- [ ] Tenant scoped
- [ ] Idempotency on writes (if applicable)
- [ ] ADR if new domain concept
- [ ] Event catalog updated

---

## Referências

- `docs/APIVersioning.md`
- `docs/DomainRegistry.md`
- `docs/ArchitectureFitnessFunctions.md` FF-API-*
- `docs/EngineeringHandbook.md`
