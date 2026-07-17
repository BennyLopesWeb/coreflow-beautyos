# Gate Review — R3-F2

| Campo | Valor |
|-------|-------|
| **Versão** | `2.2.0-r3-f2` |
| **Data** | 2026-07-16 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `FEATURE_BOOKING_CORE_ENABLED` default `true` | ✅ |
| `APP_VERSION=2.2.0-r3-f2` | ✅ |
| Commands (`create/approve/reject/cancel`) sem `_execute_legacy_path` | ✅ |
| Commands flag OFF → `BusinessRuleError` (409 via router), sem escrita | ✅ |
| Core path para de publicar `reservation.*_alias` (ADR-027 sunset) | ✅ |
| ACL `*_via_legacy` nunca delega a `ReservationService` | ✅ |
| `ReservationService` write methods removidos (fail-fast) | ✅ |
| `domain/events.py` — `logger.warning` nas factories alias | ✅ |
| Dual-write `project_*` preservado | ✅ |
| Routers `/reservations`, `/agendamentos` preservados (não deletados) | ✅ |
| Testes `test_r3_f2_reservation_service_removed.py` (novo) | ✅ 18 passed |
| Testes R1-F1/F2, R2-F0.5, R2-F1, CF6, CF9 atualizados | ✅ 65 passed (bateria completa) |
| D6 staging (`test_r2_f2b_d6_staging.py`) atualizado (sem alias; kill-switch 409) | ✅ 13 passed |
| Regressão approve/reject/cancel (`test_r2_f2_*`, `test_r2_f2b_*`) | ✅ 20 passed |
| Suíte completa backend | ✅ 372 passed, 6 skipped |
| Docs: sprint, release, ADR-027 sunset, ArchitectureDecisionLog, README sprints | ✅ |
| `.env.example` comentário `FEATURE_BOOKING_CORE_ENABLED=true` | ✅ |
| Terraform `Version` tags staging/prod → `2.2.0-r3-f2` | ✅ |

## Evidência de testes

```bash
cd backend && python -m pytest \
  tests/test_core/test_r3_f2_reservation_service_removed.py \
  tests/test_core/test_r2_f1_booking_create.py \
  tests/test_core/test_r2_f0_5_acl_wiring.py \
  tests/test_core/test_r1_f1_platform_governance.py \
  tests/test_core/test_r1_f2_platform_observability.py \
  tests/test_core/test_cf6_payments.py \
  tests/test_core/test_cf9_orders_invoices.py \
  -q -o addopts= --tb=line
# 65 passed

python -m pytest tests/test_core/test_r2_f2_booking_approve_reject.py tests/test_core/test_r2_f2b_booking_cancel.py -q -o addopts=
# 20 passed

python -m pytest -q -o addopts=
# 372 passed, 6 skipped
```

## Riscos conhecidos / Tech debt

| Item | Notas | Fase de resolução |
|------|-------|--------------------|
| `QueueEntryService.aprovar_com_horario` ainda chama `ReservationService.criar` | Sem cobertura de teste; agora sempre falha com `BusinessRuleError` ao promover fila urgente para reserva | R3-F3 (migrar fila → `/v1/bookings`) |
| Rollback não restaura path legado | Flag OFF é kill-switch, não fallback funcional — documentado em `R3-F2.md` §Rollback | N/A (decisão intencional) |

## Rollback

```bash
export FEATURE_BOOKING_CORE_ENABLED=false  # kill-switch — bloqueia escrita, não restaura legado
```

Rollback de código real: `git revert <merge-commit-r3-f2>`.

## Próximo

R3-F3 — Remover routers write `/agendamentos` (M5 RFC-003); migrar `QueueEntryService` para booking core.
