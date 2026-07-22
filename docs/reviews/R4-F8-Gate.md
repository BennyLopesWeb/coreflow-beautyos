# Gate Review — R4-F8

| Campo | Valor |
|-------|-------|
| **Versão** | `2.11.0-r4-f8` |
| **Data** | 2026-07-22 |
| **Status** | ✅ Tech PASS |

## Checklist

| Critério | Status |
|----------|--------|
| `APP_VERSION = 2.11.0-r4-f8` (`config.py`) | ✅ |
| Tags Terraform `staging`/`prod` → `2.11.0-r4-f8` | ✅ |
| Migration Alembic `cf016_r4_f8_drop_agendamentos`: `DROP TABLE agendamentos` idempotente | ✅ |
| Revision id ≤ 32 chars (`cf016_r4_f8_drop_agendamentos` — 29 chars) | ✅ |
| Downgrade recria stub mínimo (rollback de emergência, sem restauração de dados) | ✅ |
| Migration validada com round-trip completo (`upgrade`/`downgrade`/`upgrade`) contra SQLite com tabela `agendamentos` real | ✅ |
| Script legado `migrate_schema.py` espelha o DROP para o SQLite fora do Alembic (`_migrar_r4_f8_drop_agendamentos`) | ✅ |
| `app/models/agendamento.py`: `Agendamento` deixa de herdar `Base` — não mapeado, `create_all` não recria a tabela | ✅ |
| Enums (`ReservationStatus`/`StatusPagamento`/`StatusAgendamento`/`STATUS_OCUPAM_VAGA`) preservados (uso ativo por `CoreBooking`/colunas históricas) | ✅ |
| `*.agendamento_id` (`payments`/`schedules`/`fila`/`queue_entries`/`financeiro`/`notification_logs`) permanecem `Integer` simples, sem FK/join | ✅ |
| `AgendamentoService`/`ReservationService`/`PaymentReservationService` (métodos legado): reescritos para no-op (`NotFoundError`/vazio) | ✅ |
| `DisponibilidadeService`: `_expirar_agendamentos_pendentes` removido; `expirar_reservas_pendentes` só cobre `CoreBooking` | ✅ |
| `ScheduleService`: métodos `Agendamento`-typed (`_duracao_minutos`, `criar_para_reserva`) removidos (sem call-site) | ✅ |
| `QueueEntryService`: fallback legado do dia removido; `checkin`/`iniciar`/`concluir` viram no-op com log para entradas legado puras | ✅ |
| `NotificationService`: métodos `agendamento_id`-based viram no-op (log + `None`/lista vazia) | ✅ |
| `AgenteService`/`AgendaDiaService`/`AdminService`: reescritos para consultar `CoreBooking` | ✅ |
| Sync services legado→core (`CatalogLegacySyncService`, `PaymentLegacySyncService`, `OrderLegacySyncService`): no-op ou `booking_id`/`CoreBooking.legacy_agendamento_id` | ✅ |
| `booking_reconciliation_worker.detect_drift`: sempre `(0, [])`, normaliza `DRIFT` residual para `SYNCED` | ✅ |
| `LegacyPaymentQueryAdapter.is_deposit_confirmed`: só `CoreBooking.deposit_paid` | ✅ |
| `identity_service.backfill_company_id`: `Agendamento` removido da lista de models | ✅ |
| `webhook.py`/`admin.py`: imports/usos de `AgendamentoService`/`Agendamento` limpos | ✅ |
| Testes fixados para core-only (11 arquivos: cf6, cf9, r4f3, r4f4, r4f5, r4f6, r4f7, r2f5, test_agendamento_service, test_agendamentos integração, staging D6) | ✅ |
| `scripts/seed_demo_data.py`: não cria mais `Agendamento` | ✅ |
| Novo `test_r4_f8_drop_agendamentos.py` | ✅ 9/9 |
| Suíte alvo (`test_r4_f8_drop_agendamentos` + CF6 + CF9 + R4-F7 + R2-F1) | ✅ 30/30 |
| Suíte completa (`tests/`) | ✅ 435 passed / 6 skipped |
| `README.md`/`ArchitectureDecisionLog.md`/`ADR-024` atualizados (R4-F8 concluído) | ✅ |

## Testes executados

```
cd backend && python -m pytest tests/test_core/test_r4_f8_drop_agendamentos.py \
  tests/test_core/test_cf6_payments.py \
  tests/test_core/test_cf9_orders_invoices.py \
  tests/test_core/test_r4_f7_fk_decouple.py \
  tests/test_core/test_r2_f1_booking_create.py -q -o addopts= --tb=line
```

Resultado: 30 passed.

Suíte completa (`pytest tests/`): 435 passed, 6 skipped (baseline R4-F7:
425 passed, 6 skipped — +10 testes novos/reescritos, 0 regressões).

## Validação adicional (fora da suíte pytest)

- Banco SQLite de teste criado manualmente com a tabela `agendamentos`
  real (schema legado, sem FKs — equivalente ao estado pós-R4-F7) e
  stampado na revisão `cf015_r4_f7_decouple_fks`.
- `alembic upgrade head` — `agendamentos` removida com sucesso (`DROP
  TABLE`), única tabela restante no schema é `alembic_version`.
- `alembic downgrade -1` — stub mínimo de `agendamentos` recriado com
  sucesso (22 colunas, schema simplificado — sem dados, como esperado de
  um DROP destrutivo).
- `alembic upgrade head` (novamente) — `agendamentos` removida com
  sucesso outra vez, confirmando idempotência/round-trip completo.

## Débito residual documentado

- `PaymentReservationService.confirmar_deposito_por_booking` não cria
  `Financeiro` automaticamente para bookings core-only — gap aceito
  conscientemente (`FinanceiroService.registrar_entrada_automatica` já
  aceita `agendamento_id=None`, falta só o call-site).
- Reagendamento/pagamento final sem endpoint core-only equivalente —
  inalterado desde R4-F6/R4-F7.
- Rotas legado de `app/routers/pagamentos.py` (`/pagamentos/sinal` e
  correlatas) sempre falham (400) — não cobertas pelo middleware 410;
  candidatas a sunset explícito em release futura.

## Próximo

Fechar o gap de `Financeiro` para bookings core-only e avaliar sunset
explícito (410) das rotas legado de `app/routers/pagamentos.py`.
