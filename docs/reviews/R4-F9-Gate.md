# Gate Review — R4-F9

| Campo | Valor |
|-------|-------|
| **Versão** | `2.12.0-r4-f9` |
| **Data** | 2026-07-22 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.12.0-r4-f9` | ✅ |
| Tags Terraform `staging`/`prod` → `2.12.0-r4-f9` | ✅ |
| `confirmar_deposito_por_booking` registra `Financeiro` na 1ª confirmação | ✅ |
| Reconfirmação não duplica movimento Financeiro | ✅ |
| Falha Financeiro é best-effort (não reverte `deposit_paid`) | ✅ |
| `PAYMENT_LEGACY_GONE_ROUTES` + `match_legacy_gone` | ✅ |
| HTTP 410 em `/pagamentos/sinal`, `/sinal/gerar`, `/comprovante/*` | ✅ |
| Booking legado 410 preservado (R4-F1) | ✅ |
| CF9 usa `confirmar_deposito_por_booking` (sem stub Financeiro manual) | ✅ |
| Novo `test_r4_f9_financeiro_pagamentos_sunset.py` | ✅ |
| Docs sprint / release / gate / ADL | ✅ |

## Débito residual (não bloqueante)

- Endpoint core de reagendamento / pagamento final.
- Limpeza do router `pagamentos.py` (handlers mortos atrás do 410).
- Migração do frontend `pagamentoService.ts` para paths admin/booking.
