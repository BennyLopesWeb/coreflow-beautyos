# AUDIT-LEGACY-EVIDENCE-PENDING-01

Auditoria read-only dos `Payment` DEPOSIT/SINAL `PENDING` que ainda podem
carregar `valor = booking.deposit_amount` após o PR #47
(`SEPARATE-PAYMENT-EVIDENCE-01`).

## Decisão desta etapa

**Opção B** — comando administrativo em dry-run.

- Classificação pura: `backend/app/modules/payments/legacy_evidence_audit.py`
- CLI dry-run: `backend/scripts/audit_legacy_evidence_pending.py --dry-run`
- Nenhuma mutação, migration ou job de UPDATE nesta entrega.

## Corte técnico

- Merge PR #47: `2026-07-29T23:22:05Z` (`c1264c3`)
- Commit funcional: `6510803` (placeholder `0.00`)
- Deploy operacional: **não registrado** no repositório → `created_at` sozinho
  não autoriza backfill automático; pós-corte com cotação residual = `REVIEW_REQUIRED`.

## Classificação

| Classe | Significado |
|---|---|
| `candidate_backfill` | PENDING + DEPOSIT + URL + valor=cotação + sem sinais financeiros + tenant ok |
| `already_clean` | Evidência com `valor = 0.00` |
| `exclude_legitimate` | PAID / paid_at / transaction_id / final / refund / soft-delete |
| `review_required` | Qualquer ambiguidade |

## Backfill futuro (não executado)

Se aprovado depois:

1. Atualizar apenas IDs `candidate_backfill` em `Payment.valor → 0.00`
2. `sync_payment` no CorePayment espelho
3. Logar before/after por ID para rollback pontual

## Consumidores

- Admin lista cotação via `booking.deposit_amount` + `comprovante_url` (não `Payment.valor`)
- `EffectivePaidSnapshot` soma apenas status pagos → PENDING irrelevante
- Sync espelha amount; PENDING/0 não ativa reserva
