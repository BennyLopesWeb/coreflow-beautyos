# Gate Review — R3-F3

| Campo | Valor |
|-------|-------|
| **Versão** | `2.3.0-r3-f3` |
| **Data** | 2026-07-20 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| Writes `/agenda/agendamentos` removidos | ✅ 405 |
| Writes `/reservations` removidos | ✅ 405 |
| GET agenda/disponibilidade/reservations mantidos | ✅ |
| `aprovar_com_horario` → CreateBookingHandler | ✅ |
| Testes `test_r3_f3_legacy_write_routers` | ✅ |

## Dívida consciente

| Item | Release |
|------|---------|
| `/admin/agenda/*` writes ainda ativos | R3+/R4 |
| 410 Gone | R4 |
| Dual-write `project_*` | R4 |

## Próximo

R4-F1 — ✅ Implementado — 410 Gone + catalog alias. Ver [R4-F1.md](../sprints/R4-F1.md). Próximo: R4-F2 (M7 dual-write).
