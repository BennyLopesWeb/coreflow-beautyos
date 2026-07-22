# Gate Review — R4-F11

| Campo | Valor |
|-------|-------|
| **Versão** | `2.14.0-r4-f11` |
| **Data** | 2026-07-22 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.14.0-r4-f11` | ✅ |
| Tags Terraform staging/prod | ✅ |
| `RESCHEDULED` em lifecycle + ReservationStatus | ✅ |
| `RescheduleBookingHandler` + eventos | ✅ |
| `POST /v1/bookings/{id}/reschedule` | ✅ |
| Transferência `deposit_paid` | ✅ |
| Frontend `reagendar` → v1 | ✅ |
| Testes `test_r4_f11_reschedule_booking.py` | ✅ |
| Docs sprint/release/gate/ADL | ✅ |

## Débito residual (não bloqueante)

- `completed` / `no_show` / `expired` (ADR-026).
