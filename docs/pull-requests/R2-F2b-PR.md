# PR — R2-F2b Booking cancel lifecycle

Use este documento para abrir o PR quando o repositório git estiver configurado.

**Status:** D6 PASS · pronto para PR quando git remote existir

---

## Título

```
feat(booking): implement R2-F2b cancel lifecycle with CancelPolicyPort
```

## Branch sugerida

```
release/r2-f2b-booking-cancel
```

## Body (copiar para `gh pr create --body`)

```markdown
## Summary

- Implementa R2-F2b: transição **cancel** no domínio Booking com `CancelPolicyPort`, `ClockPort` e policy ≥24h (approved).
- Reutiliza padrões F2: `OutboxBatch` + defer_commit, optimistic lock, ACL dual-write, eventos lifecycle.
- Paridade **P06** (cancel pending) e **P07** (cancel approved) validadas flag ON e OFF — **305 tests passed** (+8 F2b).
- Fix legacy: `ReservationService.cancelar()` não chama `obter()` após soft-delete.

## ADRs impactadas

- [ADR-026 Amendment — Cancel Policy](docs/adr/ADR-026-Amendment-CancelPolicy.md) — **Draft** (→ Accepted pós D6)
- [ADR-025](docs/adr/ADR-025-TransactionalOutbox.md) — defer_commit cancel path
- [ADR-024](docs/adr/ADR-024-AntiCorruptionLayer.md) — `project_cancel_booking`
- [ADR-027](docs/adr/ADR-027-DomainEvents.md) — `booking.cancelled` + alias

## Checklist

- [x] `Booking.cancel()` + estado `CANCELLED`
- [x] `CancelPolicyPort` + `ClockPort`
- [x] `CancelBooking` handler + defer_commit
- [x] `POST /v1/bookings/{id}/cancel`
- [x] Eventos + alias + correlation
- [x] Paridade P06, P07 ON + OFF
- [x] Policy &lt;24h → 409
- [x] Rollback defer_commit cancel
- [x] Gate Review: `docs/reviews/R2-F2b-GateReview.md`
- [x] D6 staging PASS: `docs/reviews/R2-F2b-D6-Staging.md` (18/18)
- [x] ADR-026 Amendment → Accepted
- [ ] Sign-off D5 formal (Platform Lead)

## Test plan

- [x] `pytest -o addopts= tests/test_core/test_r2_f2b_booking_cancel.py` (8 passed)
- [x] `pytest -o addopts=` (305 passed, 6 skipped)
- [x] Staging S1–S10 — `pytest tests/test_staging/test_r2_f2b_d6_staging.py` (13 passed, 18 cenários)

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Policy timezone em produção | Adapter normaliza UTC; validar D6 com slots reais |
| Divergência flag OFF vs ON | P07 testes documentam comportamentos distintos |
| ADR ainda Draft | Não marcar Accepted até D6 |

## Rollback

```bash
export FEATURE_BOOKING_CORE_ENABLED=false
git revert <merge-commit-r2-f2b>
export APP_VERSION=1.20.0-r2-f2
```

## Referências

- Sprint: `docs/sprints/R2-F2b.md`
- Gate: `docs/reviews/R2-F2b-GateReview.md`
- Sign-off: `docs/reviews/R2-F2b-CancelPolicy-Signoff.md`
- Versão: `1.20.1-r2-f2b`
```

## Comandos (após `git init` / clone remoto)

```bash
cd "/Users/zeuser/Documents/ProjetosPessoas/Atendente Salao trancista"

git checkout -b release/r2-f2b-booking-cancel
git add backend/ docs/
git commit -m "$(cat <<'EOF'
feat(booking): R2-F2b cancel lifecycle with CancelPolicyPort

Migrate cancel to Booking domain with 24h policy, ClockPort,
OutboxBatch defer_commit, dual-write ACL, and parity P06/P07.

EOF
)"
git push -u origin HEAD

gh pr create --title "feat(booking): implement R2-F2b cancel lifecycle with CancelPolicyPort" \
  --body-file docs/pull-requests/R2-F2b-PR.md
```
