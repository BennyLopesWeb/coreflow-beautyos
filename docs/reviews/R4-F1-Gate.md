# Gate Review — R4-F1

| Campo | Valor |
|-------|-------|
| **Versão** | `2.4.0-r4-f1` |
| **Data** | 2026-07-20 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| GET/POST booking legado → 410 | ✅ |
| Link successor `/v1/bookings` | ✅ |
| disponibilidade ainda 200 | ✅ |
| `reservation.created` catalog `gone` | ✅ |
| Testes `test_r4_f1_legacy_gone` | ✅ |

## Próximo

R4-F2 — ✅ Concluído. Desligou o dual-write outbound (`project_*`) por padrão
via `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` (RFC-003 M7). Ver
[R4-F2-Gate.md](R4-F2-Gate.md).
