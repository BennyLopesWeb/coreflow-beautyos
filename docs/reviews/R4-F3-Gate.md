# Gate Review — R4-F3

| Campo | Valor |
|-------|-------|
| **Versão** | `2.6.0-r4-f3` |
| **Data** | 2026-07-21 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` removida de `config.py`/`.env.example` | ✅ |
| `booking.legacy.projection.enabled` removida de `feature_flags.py` (`feature_flags.is_enabled(...)` levanta `KeyError`) | ✅ |
| `create/approve/reject/cancel` handlers sem nenhum branch condicional de projeção | ✅ |
| `LegacyBookingAdapter` sem `project_create_booking`/`project_approve_booking`/`project_reject_booking`/`project_cancel_booking` | ✅ |
| `LegacyBookingAdapter` sem `resolve_legacy_ids`/`get_booking_legacy_id` (código morto pós-remoção) | ✅ |
| `sync_booking_from_agendamento` (inbound) preservado e funcional | ✅ |
| `*_via_legacy` (fail-fast R3-F2) preservados e funcionais | ✅ |
| Bookings sempre core-only (`legacy_agendamento_id is None`) em create/approve/reject/cancel | ✅ |
| Reconciliation não trata booking core-only como drift | ✅ |
| Reconciliation continua detectando drift em `legacy_agendamento_id` órfão (bookings históricos) | ✅ |
| Model `Agendamento`/tabela `agendamentos` **não removidos** (fora de escopo) | ✅ |
| Model `Payment`/`Schedule` legado **não removidos** (fora de escopo) | ✅ |
| Middleware 410 (`LegacyGoneMiddleware`) **não removido** (fora de escopo) | ✅ |
| Testes CF6/CF9 criam `Agendamento` via ORM direto, não via `project_create_booking` | ✅ |
| APP_VERSION `2.6.0-r4-f3` | ✅ |
| Testes `test_r4_f3_dual_write_removed.py` | ✅ 10/10 |
| Suíte completa (`tests/`) | ✅ 394 passed / 6 skipped |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f3_dual_write_removed.py \
  tests/test_core/test_r2_f1_booking_create.py \
  tests/test_core/test_r2_f2_booking_approve_reject.py \
  tests/test_core/test_r2_f2b_booking_cancel.py \
  tests/test_core/test_r4_f1_legacy_gone.py \
  tests/test_core/test_cf6_payments.py \
  tests/test_core/test_cf9_orders_invoices.py -q -o addopts= --tb=line
```

Resultado: 52 passed.

Suíte completa (`pytest tests/`): 394 passed, 6 skipped.

## Débito residual documentado

- Drop físico de `agendamentos`/`payments`/`schedules` legado → **R4-F4 ou
  posterior**, condicionado à migração/arquivamento de dados históricos e à
  confirmação de que `OrderLegacySyncService`/`InvoiceLegacySyncService`/
  `PaymentLegacySyncService`/`booking_reconciliation_worker` não precisam
  mais desses dados (ou foram eles próprios descontinuados/redirecionados).

## Próximo

R4-F4 ✅ — hard sunset (Option A, sem DROP): parou toda escrita nova em
`agendamentos` (`FilaService.aprovar_fila` → `CreateBookingHandler`,
`AgendamentoService.criar_agendamento` desativado) e moveu disponibilidade/
fila do dia para `core_bookings` como SoT. Ver
[R4-F4.md](../sprints/R4-F4.md) e [R4-F4-Gate.md](R4-F4-Gate.md). Drop
físico de `agendamentos` e models legado associados fica para **R4-F5+**,
após confirmação de zero dependência residual.
