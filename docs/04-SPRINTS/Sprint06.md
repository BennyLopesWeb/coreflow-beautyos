# Sprint 6 — core_payments + OpenTelemetry + CI MySQL

## Entregas

| Item | Status |
|------|--------|
| Tabela `core_payments` + sync | ✅ |
| API GET `/v1/payments` | ✅ |
| Evento `payment.deposit.confirmed` via outbox | ✅ |
| OpenTelemetry (`OTEL_ENABLED`) | ✅ |
| CI job `test-mysql` | ✅ |
| Alembic `cf004_payments` | ✅ |

## OpenTelemetry

```bash
OTEL_ENABLED=true make run
```

## CI MySQL

Job `test-mysql` no GitHub Actions: `alembic upgrade head` + pytest.

## Próximo: CF-7

- Plugin manifest expandido
- BeautyAgent (AI proto)
- `core_waitlist` sync
