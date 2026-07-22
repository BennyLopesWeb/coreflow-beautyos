# Gate Review — R4-F10

| Campo | Valor |
|-------|-------|
| **Versão** | `2.13.0-r4-f10` |
| **Data** | 2026-07-22 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.13.0-r4-f10` | ✅ |
| Tags Terraform staging/prod | ✅ |
| `confirmar_pagamento_final_por_booking` + Financeiro 1ª vez | ✅ |
| Exige `deposit_paid` | ✅ |
| Admin `confirmar-final` | ✅ |
| 410 `/payments/deposit`, `/payments/final` | ✅ |
| Testes `test_r4_f10_pagamento_final_core.py` | ✅ |
| Docs sprint/release/gate/ADL | ✅ |

## Débito residual (não bloqueante)

- Reagendamento core-only (R4-F11).
