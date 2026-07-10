# Scheduling Engine

Motor reutilizável de agenda — domain-agnostic.

## Estado atual

| Capacidade | Arquivo | Status |
|------------|---------|--------|
| Availability | `scheduling/engine/scheduling_engine.py` | ⚠️ Parcial |
| Conflict Detection | `scheduling/engine/resource_conflict.py` | ✅ |
| Capacity | ResourceConflictService | ✅ |
| Legacy adapter | `scheduling/engine/legacy_adapter.py` | ⚠️ Strangler |
| API availability | `/v1/scheduling/*` | ✅ |

## Componentes alvo

| Componente | Status |
|------------|--------|
| Recurring Booking | ❌ |
| Cancellation policies | ⚠️ via booking legado |
| No Show | ❌ |
| Waiting List integration | ⚠️ waitlist separado |
| Pricing Rules | ❌ |
| Notification hooks | ⚠️ via events |
| Audit trail | ❌ |

SAB: `docs/09-SCHEDULING-ENGINE/`

**Regra:** SchedulingEngine não importa `Tranca`, `Agendamento` ou terminologia beauty.
