# Gate Review — R4-F4

| Campo | Valor |
|-------|-------|
| **Versão** | `2.7.0-r4-f4` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.7.0-r4-f4` (`config.py`) | ✅ |
| Tags Terraform `staging`/`prod` → `2.7.0-r4-f4` | ✅ |
| `FilaService.aprovar_fila` não chama mais `AgendamentoService.criar_agendamento` | ✅ |
| `FilaService.aprovar_fila` cria booking via `CreateBookingHandler` (core-only, `agendamento_id` permanece `None`) | ✅ |
| `AgendamentoService.criar_agendamento` levanta `BusinessRuleError` apontando `/v1/bookings` | ✅ |
| `AgendamentoService.listar_agendamentos`/`buscar_por_id`/`obter_agendamento` preservados (leitura histórica) | ✅ |
| Nenhum outro caller de produção de `criar_agendamento`/`Agendamento(` insert fora de testes/seed | ✅ (busca `grep` confirmou único insert restante era o próprio `criar_agendamento`, removido) |
| `DisponibilidadeService._slots_ocupados` inclui `core_bookings` ativos (primário) | ✅ |
| `DisponibilidadeService._slots_ocupados` ainda lê `agendamentos` histórico ativo (leitura) | ✅ |
| P02 (double-booking) preservado — slot ocupado por `core_booking` aparece indisponível sem linha em `agendamentos` | ✅ (`test_disponibilidade_marca_slot_ocupado_por_core_booking`) |
| `QueueEntryService.processar_reservas_do_dia` processa `core_bookings` `APPROVED` do dia | ✅ |
| `QueueEntryService.processar_reservas_do_dia` não duplica bookings com `legacy_agendamento_id` (histórico dual-write) | ✅ |
| `PaymentReservationService.confirmar_deposito_por_booking` continua path primário para approve core-only | ✅ (inalterado desde R4-F2/R4-F3) |
| Endpoint admin cheap-path `POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal` | ✅ |
| Endpoint admin legado `POST /admin/pagamentos/{agendamento_id}/confirmar-sinal` preservado (histórico) | ✅ |
| Docstring `.. deprecated::` em `Agendamento` (DROP planejado R4-F5) | ✅ |
| Nenhuma migration Alembic vazia criada (sem alteração de schema nesta sprint) | ✅ (decisão: skip) |
| Model `Agendamento`/tabela `agendamentos` **não removidos** (Option A, fora de escopo o DROP) | ✅ |
| Frontend `agendamentoService.criar` sem fallback morto para rota legado `410` | ✅ |
| Testes `test_r4_f4_hard_sunset.py` | ✅ 8/8 |
| Testes de regressão atualizados (`test_agendamento_service.py`, `test_integration/test_agendamentos.py`) | ✅ |
| Suíte completa (`tests/`) | ✅ 402 passed / 6 skipped |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f4_hard_sunset.py \
  tests/test_core/test_r4_f3_dual_write_removed.py \
  tests/test_core/test_r2_f1_booking_create.py \
  tests/test_core/test_r4_f1_legacy_gone.py -q -o addopts= --tb=line
```

Resultado: 33 passed.

Suíte completa (`pytest tests/`): 402 passed, 6 skipped.

## Débito residual documentado

- DROP físico de `agendamentos`/`payments`/`schedules` legado e FKs
  associadas (`Fila.agendamento_id`, `QueueEntry.agendamento_id`,
  `Payment.agendamento_id`, `Financeiro.agendamento_id`,
  `CoreBooking.legacy_agendamento_id`) → **R4-F5**.
- Admin de pagamentos ainda dual-path (`agendamento_id` legado +
  `booking_id` novo coexistem) → reescrita completa booking-first fica
  para **R4-F5**, quando não houver mais reservas legado ativas.
- `QueueEntry`/`Fila` sem FK dedicada para `core_bookings` — dedupe da
  fila do dia usa atributos compostos (evitado adicionar coluna nova
  para não exigir migração de schema nesta sprint); revisar em R4-F5 se
  a heurística compor risco em produção.
- `QueueEntryService.checkin`/`iniciar`/`concluir` não avançam status de
  `core_bookings` para entradas core-only (gap pré-existente desde
  R4-F3 — `aprovar_com_horario` já deixava `agendamento_id=None`; não
  introduzido por esta sprint, mas documentado para correção em R4-F5).

## Próximo

R4-F5 — avaliar DROP físico de `agendamentos`/`payments`/`schedules`
legado e FKs associadas; reescrever admin de pagamentos booking-first;
fechar gap de `checkin`/`iniciar`/`concluir` para bookings core-only.
