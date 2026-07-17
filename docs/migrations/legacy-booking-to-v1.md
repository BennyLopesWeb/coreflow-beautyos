# Migração — Booking legado → CoreFlow v1

**Release:** `2.0.0-beta.1` (R2-F6) · atualizado em `2.1.0-r3-f1`  
**Escopo:** escritas de booking. Payments/fila: ver [legacy-payments-fila-to-v1.md](./legacy-payments-fila-to-v1.md) (R3-F1).

## Antes → Depois

| Legado (bloqueado em staging block) | CoreFlow v1 |
|-------------------------------------|-------------|
| `POST /agenda/agendamentos` | `POST /v1/bookings` |
| `POST /agendamentos` | `POST /v1/bookings` |
| `PUT /agenda/agendamentos/{id}` (approve/reject) | `POST /v1/bookings/{id}/approve` · `/reject` |
| `DELETE /agenda/agendamentos/{id}` | `POST /v1/bookings/{id}/cancel` |
| `POST /reservations` | `POST /v1/bookings` |
| `PUT /reservations/{id}/…` | endpoints v1 correspondentes |

## Headers de resposta (block)

```
HTTP/1.1 409 Conflict
Deprecation: true
Sunset: Sat, 01 Jan 2028 00:00:00 GMT
Link: </v1/bookings>; rel="successor-version"
X-CoreFlow-Enforcement: block
```

## Body exemplo create

```json
{
  "customer_id": 1,
  "catalog_id": 10,
  "offering_id": 20,
  "scheduled_at": "2026-08-01T10:00:00",
  "notes": "opcional"
}
```

Headers recomendados: `Idempotency-Key`, `X-Correlation-Id`, `Authorization`.

## Rollback operacional

```bash
CORE_ENFORCEMENT_MODE=warn
```

Leituras legado (`GET`) **nunca** são bloqueadas em R2.
