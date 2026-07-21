# Gate Review — R4-F2

| Campo | Valor |
|-------|-------|
| **Versão** | `2.5.0-r4-f2` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` default `false` | ✅ |
| Create booking (flag OFF) não gera `agendamentos` nem `legacy_agendamento_id` | ✅ |
| Approve/reject/cancel funcionam sem `legacy_agendamento_id` (sem `ValidationError`) | ✅ |
| `project_*` só é chamado com flag ON e id legado presente | ✅ |
| Reconciliation não trata `legacy_agendamento_id is None` como drift | ✅ |
| Reconciliation continua detectando drift com id legado órfão | ✅ |
| `QueueEntryService.aprovar_com_horario` não levanta erro sem projeção | ✅ |
| Paridade P02/P09 (slot indisponível / double-booking) preservada core-only | ✅ |
| `confirmar_deposito_por_booking` habilita approve core-only | ✅ |
| Flag ON restaura dual-write (rollback) | ✅ |
| Model `Agendamento` e rotas físicas não removidas além do já feito em R4-F1 | ✅ |
| APP_VERSION `2.5.0-r4-f2` | ✅ |
| Testes `test_r4_f2_dual_write_off.py` | ✅ 10/10 |
| Suíte completa (`tests/`) | ✅ 395 passed / 6 skipped |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f2_dual_write_off.py \
  tests/test_core/test_r2_f1_booking_create.py \
  tests/test_core/test_r2_f2_booking_approve_reject.py \
  tests/test_core/test_r2_f2b_booking_cancel.py \
  tests/test_core/test_r3_f3_legacy_write_routers.py \
  tests/test_core/test_r4_f1_legacy_gone.py \
  tests/test_core/test_r2_f5_hardening.py -q -o addopts= --tb=line
```

Resultado: 55 passed.

Suíte completa (`pytest tests/`): 395 passed, 6 skipped.

## Próximo

R4-F3 — Remover código `project_*`/`LegacyBookingAdapter` outbound e avaliar
drop de `agendamentos` após período de observação sem uso da flag de
rollback em produção.
