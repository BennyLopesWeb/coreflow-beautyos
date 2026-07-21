# ADR-024 — Dual Write Strategy & Source of Truth

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-025, ADR-027, ADR-033 |

---

## Contexto

R2 migra booking para core path com coexistência legado. Ambiguidade sobre quem é Source of Truth (SoT) gera risco de inconsistência irreversível.

## Decisão única

### Estratégia escolhida: **D) Dual-write temporário**

Com política SoT **explícita por flag** (não ambígua):

| `FEATURE_BOOKING_CORE_ENABLED` | Source of Truth | Legado `agendamentos` |
|-------------------------------|-----------------|----------------------|
| `false` | **Legacy SoT** | Autoritativo |
| `true` | **Core SoT** (`core_bookings`) | **Projeção outbound** (réplica) |

**Descartadas:**

| Alt | Motivo descarte |
|-----|-----------------|
| A) Core-only sem sync | Quebra frontend legado e paridade piloto |
| B) Legacy SoT permanente com core shadow | Core nunca assume autoridade — impede R3 sunset |
| C) Core SoT sem projeção legado | Quebra clientes legado durante transição |

### Dual-write quando flag ON

Ambas tabelas recebem write, mas **somente Core é SoT**. Legado é projeção obrigatória para compatibilidade.

### Ordem dos commits (mesma transação DB)

```
1. INSERT/UPDATE core_bookings     ← SoT
2. INSERT/UPDATE agendamentos      ← projeção (LegacyBookingPort)
3. INSERT outbox_events            ← evento canônico
COMMIT
```

Se passo 2 falhar → **ROLLBACK completo** (core não persiste sem projeção enquanto legado consumers existem).

### Rollback operacional

| Ação | Efeito |
|------|--------|
| Flag OFF | Volta Legacy SoT; core rows orphan acceptable (reconciliation) |
| Git revert PR | Flag OFF + revert code |
| Reconciliation detecta drift | Alert + manual fix script |

### Compensação

| Falha | Compensação |
|-------|-------------|
| Core committed, legacy failed | Impossível by design — same TX rollback |
| Outbox publish failed | Retry worker; core+legacy already consistent |
| Legacy read stale | Frontend legado reads agendamentos — updated in same TX |

### Reconciliação (R2-F5)

Job periódico (5 min):

- Compare `core_bookings.legacy_id` ↔ `agendamentos.id`
- Compare status mapping
- Metric `coreflow.booking.legacy_sync.drift_count`
- Alert if >0 for >15 min

### Idempotência

- POST create: `Idempotency-Key` header → dedupe table (ADR-031)
- Retry safe: same key returns same booking_id

### Timeout & retries

| Operação | Timeout | Retries |
|----------|---------|---------|
| Legacy projection write | 3s | 0 (fail TX) |
| Outbox worker publish | 30s | 5 exponential |
| Reconciliation job | 60s | 1 |

### Monitoramento

| Métrica | Alert |
|---------|-------|
| `drift_count` | >0 WARNING, >10 CRITICAL |
| `legacy_projection_failures` | >0 CRITICAL |
| `core_path_latency_p99` | >500ms WARNING |

### Sunset dual-write

| Milestone | Ação |
|-----------|------|
| R2-F6 | Block legado writes (staging) |
| R3-F1 | Block produção; stop projection writes |
| R3-F2 | Remove booking write path legado (`ReservationService`) — `project_*` outbound permanece ativo |
| R4-F2 | ✅ `FEATURE_BOOKING_LEGACY_PROJECTION_ENABLED` default `false` — `project_*` deixa de ser chamado por padrão (código mantido para rollback) |
| R4-F3 | Remover código `project_*` / `LegacyBookingAdapter` outbound |
| R4+ | Drop agendamentos table (separado ADR), após período de observação sem uso da flag |

## Consequências

- Transação única core+legacy+outbox (ADR-025)
- Reconciliation job obrigatório F5
- `sync_status` field em core_bookings: `synced`, `pending`, `drift`

## Referências

- ADR-004 Strangler Fig
- RFC-003 §12 Legacy sunset
