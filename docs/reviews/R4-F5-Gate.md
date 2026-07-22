# Gate Review — R4-F5

| Campo | Valor |
|-------|-------|
| **Versão** | `2.8.0-r4-f5` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.8.0-r4-f5` (`config.py`) | ✅ |
| Tags Terraform `staging`/`prod` → `2.8.0-r4-f5` | ✅ |
| Migration Alembic `cf013_r4_f5_booking_id` adiciona `booking_id` (FK nullable indexada) em `queue_entries`/`fila`, idempotente | ✅ |
| Script legado `migrate_schema.py` espelha as colunas para o SQLite fora do Alembic | ✅ |
| `QueueEntryService.aprovar_com_horario` seta `entry.booking_id` | ✅ |
| `QueueEntryService.processar_reservas_do_dia`/`_processar_core_bookings_do_dia` seta `booking_id` na `QueueEntry` criada a partir de `core_bookings` | ✅ |
| Dedupe de `_processar_core_bookings_do_dia` prioriza `booking_id` (fallback por atributos compostos preservado para linhas sem `booking_id`) | ✅ |
| `QueueEntryService.checkin` avança `CoreBooking.status` → `CHECKED_IN` para entrada com `booking_id` | ✅ |
| `QueueEntryService.iniciar` avança `CoreBooking.status` → `IN_SERVICE` para entrada com `booking_id` | ✅ |
| `QueueEntryService.concluir` avança `CoreBooking.status` → `COMPLETED` para entrada com `booking_id` | ✅ |
| Entradas legado puras (`agendamento_id`, sem `booking_id`) continuam com fallback `Agendamento`/`ReservationService` inalterado | ✅ |
| `FilaService.aprovar_fila` seta `fila.booking_id` | ✅ |
| `DisponibilidadeService` revisado — já core-primary desde R4-F4, sem regressão | ✅ |
| Endpoint legado `POST /admin/pagamentos/{agendamento_id}/confirmar-sinal` marcado `deprecated=True` no OpenAPI + docstring | ✅ |
| Endpoint booking-first `POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal` inalterado (path primário) | ✅ |
| `QueueEntryResponse`/`FilaResponse`/`FilaItemDetalhado` expõem `booking_id` | ✅ |
| `DROP TABLE agendamentos`/`payments`/`schedules` **não executado** (fora de escopo, adiado para R4-F6) | ✅ |
| Nenhuma remoção de FK física legado nesta sprint (bloqueado por `Payment`/`Schedule` sem par core) | ✅ |
| Testes `test_r4_f5_core_ops.py` (novo) | ✅ 6/6 |
| Pin de versão relaxado em `test_r4_f4_hard_sunset.py::test_app_version_r4_f4` | ✅ |
| Suíte completa (`tests/`) | ✅ 408 passed / 6 skipped |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f5_core_ops.py \
  tests/test_core/test_r4_f4_hard_sunset.py \
  tests/test_core/test_r4_f3_dual_write_removed.py -q -o addopts= --tb=line
```

Resultado: 24 passed.

Suíte completa (`pytest tests/`): 408 passed, 6 skipped.

## Débito residual documentado

- DROP físico de `agendamentos`/`payments`/`schedules` legado e FKs
  associadas → **R4-F6**, condicionado à migração de `Payment`/
  `Schedule` legado para modelos core dedicados (bloqueio físico atual:
  esses dois domínios ainda não têm par core).
- Admin de pagamentos ainda dual-path — endpoint legado marcado
  `deprecated=True` nesta sprint, mas não removido (reservas históricas
  ativas); reescrita completa booking-first → **R4-F6**.
- Sem backfill retroativo de `booking_id` para registros de
  `QueueEntry`/`Fila` criados antes desta release — dedupe por
  atributos compostos preservado como fallback para esses casos.

## Próximo

R4-F6 — migrar `Payment`/`Schedule` legado para o core, completar a
reescrita do admin de pagamentos booking-first e executar o DROP físico
de `agendamentos`/`payments`/`schedules` legado e FKs associadas.
