# Sprint 5 — Customer + Outbox + Booking v1 Frontend

**Objetivo:** `core_customers`, outbox de eventos, `booking.created`, frontend POST `/v1/bookings`.

## Entregas

| Item | Status |
|------|--------|
| Tabela `core_customers` + sync legado | ✅ |
| API GET `/v1/customers` | ✅ |
| Tabela `core_event_outbox` + `OutboxService` | ✅ |
| Evento `booking.created` + handler | ✅ |
| `reservation.created` via outbox | ✅ |
| Alembic `cf003_customers_outbox` | ✅ |
| Frontend `criarBookingV1` + fallback | ✅ |
| OpenTelemetry | 🔜 CF-6 |

## Outbox

```
OutboxService.record_and_publish(event)
  → INSERT core_event_outbox (pending)
  → event_bus.publish
  → status = processed
```

Eventos: `reservation.created`, `booking.created`

## Frontend

```
agendamentoService.criar
  → coreflowService.criarBookingV1 (POST /v1/bookings)
  → fallback /agenda/agendamentos
```

## Próximo: CF-6

- `core_payments` sync
- OpenTelemetry
- CI job MySQL
