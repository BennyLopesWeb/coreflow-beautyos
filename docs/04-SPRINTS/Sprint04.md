# Sprint 4 — Scheduling Engine + Resource Engine

**Objetivo:** Motor genérico de availability/conflict baseado em Resource + ScheduleBlock.

## Entregas

| Item | Status |
|------|--------|
| `SchedulingEngine` | ✅ |
| `ResourceConflictService` (capacity) | ✅ |
| `LegacySchedulingAdapter` (Strangler merge) | ✅ |
| `POST /v1/scheduling/conflicts` | ✅ |
| Availability via engine (não só legado) | ✅ |
| `ResourceType` estendido (professional, vehicle…) | ✅ |
| Testes engine (3 novos) | ✅ |
| Docs 00, 06, 07, 09 stubs | ✅ |
| `core_customers` + Outbox | 🔜 CF-5 |

## Arquitetura

```
modules/scheduling/engine/
  scheduling_engine.py      # check_availability, detect_conflict
  resource_conflict.py      # core_schedule_blocks + capacity
  legacy_adapter.py         # merge com Agendamento legado
```

## API nova

```bash
POST /v1/scheduling/conflicts
{
  "resource_id": 1,
  "starts_at": "2026-07-15T10:00:00",
  "ends_at": "2026-07-15T12:00:00"
}
```

## Próximo: CF-5

- `core_customers` + `/v1/customers`
- Outbox pattern + eventos booking.*
- OpenTelemetry
