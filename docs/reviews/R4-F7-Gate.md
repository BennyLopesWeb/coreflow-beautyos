# Gate Review — R4-F7

| Campo | Valor |
|-------|-------|
| **Versão** | `2.10.0-r4-f7` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.10.0-r4-f7` (`config.py`) | ✅ |
| Tags Terraform `staging`/`prod` → `2.10.0-r4-f7` | ✅ |
| Migration Alembic `cf015_r4_f7_decouple_agendamento_fks`: remove FK física para `agendamentos` de `payments`/`schedules`/`satisfaction_surveys`/`fila`/`queue_entries`/`financeiro`/`notification_logs`; `schedules`/`satisfaction_surveys` ganham `agendamento_id` nullable + `booking_id` (FK nullable indexada) | ✅ |
| Migration idempotente (compatível com `create_all` em testes) | ✅ |
| Migration validada com round-trip completo (`upgrade`/`downgrade`/`upgrade`) contra banco com schema legado real (sete tabelas com FK física, `schedules`/`satisfaction_surveys` com `agendamento_id NOT NULL`) | ✅ |
| Script legado `migrate_schema.py` espelha a migração para o SQLite fora do Alembic (`_migrar_r4_f7_decouple_agendamento_fks`, recria tabela via `PRAGMA foreign_key_list`) | ✅ |
| `app/models/schedule.py`/`satisfaction_survey.py`: FK física removida + `booking_id` novo | ✅ |
| `app/models/payment.py`/`fila.py`/`queue_entry.py`/`financeiro.py`/`notification_log.py`: FK física removida de `agendamento_id` (colunas/nullability inalteradas fora isso) | ✅ |
| Relationships `Agendamento`→backref removidas (sem call-site ativo confirmado via grep) | ✅ |
| `DisponibilidadeService._slots_ocupados`: leitura de compatibilidade sobre `Agendamento` legado removida — `core_bookings` única fonte de ocupação | ✅ |
| `ScheduleService.criar_para_reserva`: docstring atualizada, sem mudança de comportamento (sem call-site ativo) | ✅ |
| `app/models/agendamento.py`: docstring atualizada — DROP físico planejado para R4-F8 | ✅ |
| `DROP TABLE agendamentos`/`payments`/`schedules` **não executado** (fora de escopo, adiado para R4-F8) | ✅ |
| Testes `test_r4_f7_fk_decouple.py` (novo) | ✅ 7/7 |
| `test_r4_f4_hard_sunset.py::test_disponibilidade_ainda_ve_agendamento_historico` reescrito (comportamento invertido, documentado) | ✅ |
| Pin de versão relaxado em `test_r4_f6_payment_bridge.py::test_app_version_r4_f6` | ✅ |
| Suíte alvo (`test_r4_f7_fk_decouple` + CF6 + CF9 + R4-F6) | ✅ 25/25 |
| Suíte completa (`tests/`) | ✅ 425 passed / 6 skipped |
| `README.md`/`ArchitectureDecisionLog.md`/`ADR-024` atualizados (R4-F7 concluído, R4-F8 próximo) | ✅ |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f7_fk_decouple.py \
  tests/test_core/test_cf6_payments.py \
  tests/test_core/test_cf9_orders_invoices.py \
  tests/test_core/test_r4_f6_payment_bridge.py -q -o addopts= --tb=line
```

Resultado: 25 passed.

Suíte completa (`pytest tests/`): 425 passed, 6 skipped (baseline R4-F6: 418
passed, 6 skipped — +7 testes novos, 0 regressões).

## Validação adicional (fora da suíte pytest)

- `alembic upgrade head` / `alembic downgrade -1` / `alembic upgrade head`
  executados manualmente contra um banco SQLite com o schema legado real
  (sete tabelas com FK física para `agendamentos`; `schedules`/
  `satisfaction_surveys` com `agendamento_id NOT NULL`, sem `booking_id`) —
  round-trip bem-sucedido, dados preservados em todas as sete tabelas, FKs
  corretamente removidas no upgrade e restauradas no downgrade.
- `_migrar_r4_f7_decouple_agendamento_fks` (script `migrate_schema.py`)
  executado manualmente contra as sete tabelas com schema legado — recria
  preservando dados, idempotente em segunda execução (detecta via
  `PRAGMA foreign_key_list`, funciona independentemente de
  `PRAGMA foreign_keys` estar ligado).
- `alembic upgrade head` a partir de banco vazio (só tabelas `core_*`
  criadas por `cf001`-`cf014`) confirma que a migration no-opa
  corretamente quando as tabelas legado (`payments`/`schedules`/etc.,
  criadas via `Base.metadata.create_all()` fora do Alembic) não existem.

## Débito residual documentado

- DROP físico de `agendamentos`/`payments`/`schedules` legado → **R4-F8**,
  condicionado à migração/arquivamento de dados históricos e confirmação
  de que não há mais consumidores lendo dados legado.
- `AdminService.listar_pagamentos` ainda lista somente `Agendamento`
  legado — bookings core-only não aparecem na tela admin de pagamentos
  (débito herdado de R4-F6, inalterado).
- Disponibilidade não bloqueia mais slot por `Agendamento` histórico ativo
  — aceito conscientemente (mitigado por `expirar_reservas_pendentes`,
  que continua ativo para dados legado pendentes).
- Reagendamento (`solicitar_reagendamento`/`aceitar_reagendamento`) sem
  endpoint core equivalente — inalterado desde R4-F6.

## Próximo

R4-F8 — DROP físico de `agendamentos`/`payments`/`schedules` legado
(nenhuma FK física restante desde R4-F7), migração/arquivamento de dados
históricos, e reescrita de `AdminService.listar_pagamentos` para incluir
bookings core-only.
