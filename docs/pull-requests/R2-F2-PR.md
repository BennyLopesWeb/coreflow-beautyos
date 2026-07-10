# PR — R2-F2 Booking approve/reject lifecycle

Use este documento para abrir o PR quando o repositório git estiver configurado.

---

## Título

```
feat(booking): implement R2-F2 approval/rejection lifecycle with optimistic locking
```

## Branch sugerida

```
release/r2-f2-booking-approve-reject
```

## Body (copiar para `gh pr create --body`)

```markdown
## Summary

- Implementa R2-F2: transições de lifecycle **approve** e **reject** no domínio Booking com state machine, optimistic lock e `PaymentQueryPort`.
- Resolve **TD-R2-F1b-001** via `OutboxBatch` + `defer_commit` no core path (create, approve, reject).
- Mantém `POST /v1/bookings` congelado (R2-F1/F1b); mudanças limitadas a `POST .../approve` e `POST .../reject`.
- Paridade P03, P04, P05, P08 validada flag ON e OFF — **297 tests passed**.

## Checklist

- [x] ADR R2-F2 (026, 028, 031, 025, 024, 027, 030)
- [x] Outbox defer_commit (`OutboxBatch`)
- [x] State machine (`Booking.approve()`, `Booking.reject()`)
- [x] Optimistic lock (`save_with_version`, ETag, If-Match)
- [x] PaymentQueryPort + LegacyPaymentQueryAdapter
- [x] Eventos lifecycle + alias + correlation_id + version
- [x] Paridade tests P03–P05, P08
- [x] Rollback / defer_commit tests
- [x] Gate Review: `docs/reviews/R2-F2-GateReview.md`
- [x] Sprint doc + Decision Log atualizados

## Test plan

- [x] `pytest -o addopts= tests/test_core/test_r2_f2_booking_approve_reject.py`
- [x] `pytest -o addopts=` (297 passed)
- [x] FF-BKG-001 — `tests/test_core/test_r2_f0_5_acl_wiring.py`
- [ ] Staging: approve/reject 48h com `FEATURE_BOOKING_CORE_ENABLED=true` (operacional pós-merge)

## Notas

- Legacy approve/reject mantém `record_and_publish()` — TD-R2-F2-001 (baixa, opcional F2b).
- Próximo: R2-F2b cancel — doc em `docs/sprints/R2-F2b.md` (sem código até sign-off domínio §7).

## Referências

- Sprint: `docs/sprints/R2-F2.md`
- Gate: `docs/reviews/R2-F2-GateReview.md`
- Versão: `1.20.0-r2-f2`
```

## Comandos (após `git init` / clone remoto)

```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/Atendente Salao trancista"

git checkout -b release/r2-f2-booking-approve-reject
git add backend/ docs/
git commit -m "$(cat <<'EOF'
feat(booking): R2-F2 approve/reject lifecycle with optimistic locking

Migrate approve and reject to Booking domain with state machine,
PaymentQueryPort, OutboxBatch defer_commit, and parity tests P03-P08.

EOF
)"
git push -u origin HEAD

gh pr create --title "feat(booking): implement R2-F2 approval/rejection lifecycle with optimistic locking" \
  --body-file docs/pull-requests/R2-F2-PR.md
```

> **Nota:** Este workspace não possui repositório git nem `gh` CLI no ambiente atual. Execute os comandos acima no ambiente com remote configurado.
