# 09 — Scheduling Engine

Motor genérico de reservas. **Não sabe** se reserva cadeira, quadra ou consultório — apenas Resources com capacity.

## Capacidades

| Capacidade | Status | Implementação |
|------------|--------|---------------|
| Availability | ✅ | `SchedulingEngine.check_availability` |
| Conflict Detection | ✅ | `ResourceConflictService` + `POST /v1/scheduling/conflicts` |
| Capacity | ✅ | `CoreResource.capacity` |
| Reservation | ⚠️ | CQRS CreateBooking + legado |
| Recurring | 🔜 | — |
| Waitlist | ⚠️ | `Fila` legado |
| Check-in/out | 🔜 | — |
| Cancellation | ⚠️ | legado |
| No-show | 🔜 | — |
| Pricing | ⚠️ | snapshot booking |
| Notification | ⚠️ | mock |
| Audit | 🔜 | — |

## Arquitetura

```
GET /v1/scheduling/availability
    → SchedulingAvailabilityService
    → SchedulingEngine
        → ResourceConflictService (core_schedule_blocks)
        → LegacySchedulingAdapter (merge Strangler)
```

## Código

```
backend/app/modules/scheduling/engine/
  scheduling_engine.py
  resource_conflict.py
  legacy_adapter.py
```

Ver [`07-META-MODEL/README.md`](../07-META-MODEL/README.md) · [`COREFLOW_GAP_ANALYSIS.md`](../COREFLOW_GAP_ANALYSIS.md)
