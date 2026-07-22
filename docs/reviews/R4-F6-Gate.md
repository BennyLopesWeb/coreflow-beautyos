# Gate Review — R4-F6

| Campo | Valor |
|-------|-------|
| **Versão** | `2.9.0-r4-f6` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.9.0-r4-f6` (`config.py`) | ✅ |
| Tags Terraform `staging`/`prod` → `2.9.0-r4-f6` | ✅ |
| Migration Alembic `cf014_r4_f6_payment_booking_id`: `payments.agendamento_id` nullable + `payments.booking_id` (FK nullable indexada), idempotente | ✅ |
| Migration validada com round-trip completo (`upgrade`/`downgrade`/`upgrade`) contra banco com schema legado real (`NOT NULL` físico) | ✅ |
| Script legado `migrate_schema.py` espelha a migração para o SQLite fora do Alembic (recria tabela quando `NOT NULL` físico ainda presente) | ✅ |
| `app/models/payment.py`: `agendamento_id` nullable + `booking_id` novo | ✅ |
| `PaymentReservationService.criar_pendente` aceita `booking_id` sem `agendamento_id`; recusa (`BusinessRuleError`) quando ambos ausentes | ✅ |
| `confirmar_deposito_por_booking` cria/atualiza `Payment` ponte vinculado por `booking_id` (best-effort, não bloqueia a confirmação) | ✅ |
| `confirmar_deposito`/`confirmar_pagamento_final` (legado) inalterados — CF6/CF9 continuam passando | ✅ |
| `DisponibilidadeService._slots_ocupados` — docstring revisada, `core_bookings` explicitamente única fonte de ocupação para bookings novos | ✅ |
| `DisponibilidadeService.expirar_reservas_pendentes` expira também `CoreBooking` pendente/sem sinal via `CancelBookingHandler` | ✅ |
| `ReservationService.aceitar_reagendamento` não chama mais `ScheduleService.criar_para_reserva` | ✅ |
| Model `Schedule` mantido (sem DROP) | ✅ |
| `POST /admin/pagamentos/{agendamento_id}/confirmar-sinal` retorna `410 Gone` com `successor` | ✅ |
| `POST /admin/pagamentos/booking/{booking_id}/confirmar-sinal` inalterado (path único) | ✅ |
| Frontend: `adminService.confirmarSinalBooking` novo; `pagamentos.tsx` trata 410 da rota legado | ✅ |
| `DROP TABLE agendamentos`/`payments`/`schedules` **não executado** (fora de escopo, adiado para R4-F7) | ✅ |
| Testes `test_r4_f6_payment_bridge.py` (novo) | ✅ 10/10 |
| Pin de versão relaxado em `test_r4_f5_core_ops.py::test_app_version_r4_f5` | ✅ |
| Suíte alvo (`test_r4_f6_payment_bridge` + CF6 + CF9 + R4-F5 + R4-F4) | ✅ 32/32 |
| Suíte completa (`tests/`) | ✅ 418 passed / 6 skipped |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f6_payment_bridge.py \
  tests/test_core/test_cf6_payments.py \
  tests/test_core/test_cf9_orders_invoices.py \
  tests/test_core/test_r4_f5_core_ops.py \
  tests/test_core/test_r4_f4_hard_sunset.py -q -o addopts= --tb=line
```

Resultado: 32 passed.

Suíte completa (`pytest tests/`): 418 passed, 6 skipped (baseline R4-F5: 408 passed, 6 skipped — +10 testes novos, 0 regressões).

## Validação adicional (fora da suíte pytest)

- `alembic upgrade head` / `alembic downgrade -1` / `alembic upgrade head`
  executados manualmente contra um banco SQLite com o schema legado real
  (`payments.agendamento_id NOT NULL`, sem `booking_id`, com o grafo
  completo de tabelas legado/core via `init_db()`) — round-trip
  bem-sucedido, dados preservados.
- `_migrar_r4_f6_payment_booking_id` (script `migrate_schema.py`)
  executado manualmente contra tabela `payments` com schema legado —
  recria a tabela preservando dados, idempotente em segunda execução.

## Débito residual documentado

- DROP físico de `agendamentos`/`payments`/`schedules` legado e FKs
  associadas → **R4-F7**, condicionado à remoção das últimas FKs físicas
  (`Schedule.agendamento_id`, `SatisfactionSurvey.agendamento_id`) e
  confirmação de que não há mais consumidores lendo dados legado.
- `AdminService.listar_pagamentos` ainda lista somente `Agendamento`
  legado — bookings core-only não aparecem na tela admin de pagamentos.
- Reagendamento (`solicitar_reagendamento`/`aceitar_reagendamento`) sem
  endpoint core equivalente — continua restrito a `Agendamento` legado
  histórico, sem router HTTP ativo.

## Próximo

R4-F7 — remover FKs físicas restantes de `Schedule`/`SatisfactionSurvey`,
executar o DROP físico de `agendamentos`/`payments`/`schedules` legado, e
migrar `AdminService.listar_pagamentos` para incluir bookings core-only.
