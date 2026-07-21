# RFC-003 — Core Domain Consolidation (Release 2)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aprovado pelo ARB (2026-07-09) |
| **Autor** | Architecture Review Board — CoreFlow |
| **Data** | 2026-07-09 |
| **Release** | R2 — Core Domain Consolidation |
| **Versão alvo** | `1.19.0-r2-f1` → `2.0.0-beta.1` |
| **ADRs vinculados** | ADR-009–011, ADR-024–033 |
| **Pré-requisitos** | Release 1 ✅ · Documentação estratégica v3 ✅ |

---

## 1. Objetivo

Consolidar o **Core Framework** da CoreFlow Platform mediante:

1. Extração do **Booking** para domínio puro (aggregate root, state machine, eventos canônicos).
2. Introdução do **Resource Engine v1** desacoplado de terminologia vertical.
3. Formalização do **Plugin Engine** com lifecycle, hooks tipados e isolamento.
4. Padronização **hexagonal** (ports, repositories, ACL) em Booking, Catalog, Customer, Scheduling e Payments.
5. Eliminação de ambiguidades de **dual-write**, transações, idempotência e enforcement.

Esta RFC estabelece **um único caminho de implementação** para a Release 2.

---

## 2. Motivação

### Problema

O repositório opera em **Strangler Fig** (ADR-004): commands CQRS de booking ainda delegam a `ReservationService` e `LegacySyncService` diretamente; scheduling referencia `legacy_tranca_id`; `BeautyAgent` permanece em `modules/ai/`. A documentação v3 define a plataforma multi-domínio, mas **decisões normativas** sobre SoT, transações e state machine não estavam fechadas — impedindo implementação sem risco de retrabalho.

### Por que agora

- Release 1 entregou governança, ACL wired parcialmente, flags, telemetria.
- PMM Nível 1 completo; transição para Nível 2 exige core domain consolidado.
- Releases 3–6 (Integration Hub, BRE, Marketplace) dependem de fronteiras claras R2.

### Matriz de decisão — abordagem R2

| Alternativa | Prós | Contras | Decisão |
|-------------|------|---------|---------|
| Big-bang rewrite | Simplicidade final | Quebra piloto, perda regras | ❌ Rejeitada |
| Manter delegação legado | Zero risco curto prazo | Nunca vira plataforma | ❌ Rejeitada |
| **Strangler incremental com ADRs fechados** | Paridade, rollback, flags | Complexidade temporária | ✅ **Escolhida** |
| Microserviços por contexto | Escala independente | Prematuro (Constituição) | ❌ Rejeitada |

---

## 3. Escopo IN

| # | Item | Fase |
|---|------|------|
| 1 | RFC-003 + ADR-009–033 | R2-F0 |
| 2 | ACL wiring nos commands (ports only) | R2-F0.5 |
| 3 | Booking create domain path | R2-F1, R2-F1b |
| 4 | Booking approve/reject/cancel | R2-F2, R2-F2b |
| 5 | Resource Engine v1 + SchedulingPort→ResourcePort | R2-F3 |
| 6 | Repos hexagonal Catalog + Customer | R2-F3b |
| 7 | Plugin Engine formal + BeautyAgent migration | R2-F4 |
| 8 | Fitness CI ERROR + observability + reconciliation | R2-F5 |
| 9 | Enforcement block narrow + release beta | R2-F6 |
| 10 | Matriz paridade ≥12 cenários | R2-F0 |
| 11 | Fitness functions expandidas por fase | R2-F0 → F5 |

---

## 4. Escopo OUT

| Item | Release | Motivo |
|------|---------|--------|
| Integration Hub implementation | R3 | Design only (`IntegrationHub.md`) |
| Tenant Customization Engine | R3 | Design only |
| Business Rules Engine | R4 | Design only |
| Low-Code Platform | R4 | Design only |
| BI / ML predictions | R3–R4 | Read models R3 |
| Marketplace / API Marketplace | R5 | Design only |
| CLI completa | R6 | Design only |
| Scheduling Engine v2 | R3 | Resource Engine v1 prerequisite |
| Microserviços | 2028+ | ADR-013 criteria |
| Remoção física código legado | R3+ | Block only em R2-F6 |
| Sports/Clinic produção | R3+ | Stubs enriquecidos R2-F4 |
| Frontend SDK admin tab | R3 | Opcional; não gate R2 |
| Reschedule completo | R3 | Policy ADR-026: legado until R3 |
| No-show automático | R4 | Event stub only |

---

## 5. Estratégia de migração

### Princípios (Constituição + ADR-004)

1. **Uma fase = um PR = uma versão semver.**
2. **Feature flag default false** em toda migração comportamental.
3. **ACL obrigatória** — zero import direto `app/services/` em `modules/booking/application/`.
4. **Paridade antes de enforcement block.**
5. **Core SoT quando flag ON** (ADR-024) — legado é projeção outbound.

### Sequência oficial (único caminho)

```
R2-F0   → Governança (RFC + ADRs + paridade + fitness baseline)
R2-F0.5 → ACL wiring (commands → ports/adapters)
R2-F1   → Booking create (domain + repository)
R2-F1b  → Idempotency + correlation_id + booking.created
R2-F2   → Approve / Reject + PaymentQueryPort
R2-F2b  → Cancel + state machine completa R2
R2-F3   → Resource Engine v1 + ResourcePort
R2-F3b  → Catalog + Customer repositories
R2-F4   → Plugin Engine + BeautyAgent migration
R2-F5   → Fitness CI ERROR + OTEL + reconciliation job
R2-F6   → Enforcement block narrow + 2.0.0-beta.1
```

### Rollout por ambiente

| Ambiente | Sequência |
|----------|-----------|
| **Local/Dev** | Flag ON por desenvolvedor após paridade local |
| **Staging** | Flag ON após DoD da fase; canary tenant `company_id` fixo documentado em sprint doc |
| **Produção piloto** | Flag ON após 7 dias staging sem incidente P1; 1 tenant canary → 100% |
| **Produção geral** | Após F6 block em staging validado |

---

## 6. Feature Flags

| Flag | Env var | Default | Owner | Fases | Sunset |
|------|---------|---------|-------|-------|--------|
| Booking core path | `FEATURE_BOOKING_CORE_ENABLED` | `false` | Platform Team | F1–F2b | R3-F1 (remove legado path) |
| Resource Engine | `FEATURE_RESOURCE_ENGINE_ENABLED` | `false` | Platform Team | F3 | R3-F2 |
| Plugin Engine | `FEATURE_PLUGIN_ENGINE_ENABLED` | `false` | Platform Team | F4 | R3-F3 |
| SDK Bookings UI | `EXPO_PUBLIC_USE_SDK_BOOKINGS` | `false` | Frontend Team | R3 | R3-F4 |
| Core enforcement | `CORE_ENFORCEMENT_MODE` | `warn` | Platform Team | F6 | R4 (remove legado routes) |

Detalhes lifecycle: **ADR-032**.

---

## 7. Critérios de sucesso

| # | Critério | Métrica | Fase gate |
|---|----------|---------|-----------|
| S1 | Booking domain puro | Zero `ReservationService` em commands | F2 ERROR |
| S2 | ACL compliance | Zero `LegacySyncService` direto em commands | F2 ERROR |
| S3 | Resource Engine | `/v1/resources` CRUD tenant-scoped | F3 |
| S4 | Beauty separated | Zero `BeautyAgent` em `modules/ai/` | F4 |
| S5 | Paridade booking | 12/12 cenários PASS flag ON | F2b |
| S6 | Testes | ≥300 pytest passing | F5 |
| S7 | Coupling | ≤3 identified couplings | F5 |
| S8 | Events | `booking.*` canônicos; `reservation.*` alias only | F1b |
| S9 | Idempotency | POST `/v1/bookings` documentado + testado | F1b |
| S10 | Enforcement | Block narrow booking routes staging | F6 |
| S11 | Architecture score | ≥6.5 | F6 |
| S12 | PMM L2 partial | ≥65% critérios L2 (ver PMM doc) | F6 |

---

## 8. Critérios de rollback

| Gatilho | Ação | Tempo alvo |
|---------|------|------------|
| Paridade test FAIL | Flag OFF + revert PR | <15 min |
| Dual-write drift >0.1% | Flag OFF + reconciliation manual | <1 h |
| P1 produção piloto | Flag OFF all tenants | <5 min |
| Enforcement block quebra cliente | `CORE_ENFORCEMENT_MODE=warn` | <5 min |
| Schema migration fail | Alembic downgrade + revert PR | <30 min |

Cada sprint doc **deve** listar env vars exatas e comando git revert.

---

## 9. Critérios de aprovação (RFC)

- [x] ADR-009–011, 024–033 aceitos pelo ARB
- [x] Matriz paridade ≥12 cenários publicada
- [x] Fitness functions por fase definidas
- [x] PMM L2 partial exit criteria atualizados
- [ ] Stakeholder sign-off explícito (product + engineering)
- [ ] Staging canary tenant identificado
- [ ] Architecture Board approval registrada

---

## 10. Riscos

| Risco | Prob. | Impacto | Mitigação | Owner |
|-------|-------|---------|-----------|-------|
| Dual-write inconsistency | Média | Crítico | ADR-024/025 + reconciliation F5 | Platform |
| Scheduling legado até F3 | Alta | Alto | SchedulingPort interim F1 | Platform |
| Payment approve chain break | Média | Alto | PaymentQueryPort + paridade cenário 6 | Platform |
| Plugin hook regression | Média | Médio | Flag + fallback inline | Platform |
| Enforcement block amplo | Baixa | Alto | ADR-033 narrow scope | Platform |
| Flag debt | Média | Médio | ADR-032 lifecycle | Platform |
| PMM L2 expectativa errada | Média | Médio | Comunicar partial 65% R2 | ARB |

Registro completo: `docs/reviews/R2-ArchitectureRiskRegister.md`.

---

## 11. Métricas

| Métrica | Ferramenta | Threshold R2 |
|---------|----------|--------------|
| `coreflow.booking.core_path.requests` | Prometheus | Track flag ON/OFF |
| `coreflow.booking.legacy_sync.drift_count` | Reconciliation job | 0 |
| `coreflow.booking.paridade.pass_rate` | CI | 100% |
| `coreflow.api.legacy_write_ratio` | Architecture metrics | ↓ por rota booking |
| `coreflow.fitness.violations` | CI | 0 ERROR |
| `coreflow.feature_flag.enabled` | OTEL/Prometheus | per flag |
| Readiness score average | `/v1/platform/readiness-score` | ≥45 R2 exit |

---

## 12. Plano de sunset do legado

| Milestone | Ação | Release |
|-----------|------|---------|
| M1 | Headers Deprecation/Sunset em rotas booking legado | R2-F6 |
| M2 | `CORE_ENFORCEMENT_MODE=block` rotas booking (staging) | R2-F6 |
| M3 | Block produção piloto booking writes legado | R3-F1 |
| M4 | Remover `ReservationService` booking paths | R3-F2 ✅ Implemented |
| M5 | Remover routers `/agendamentos` write | R3-F3 ✅ (`2.3.0-r3-f3`) |
| M6 | `410 Gone` rotas legado booking | R4 |
| M7 | Remover `legacy_sync` booking outbound | R4 |

**Nomenclatura eventos:** `reservation.*` alias até R3-F2; sunset ADR-027.

---

## 13. Referências

| Documento | Path |
|-----------|------|
| R2 Execution Plan v4 | `docs/R2-ExecutionPlan.md` |
| Constituição | `docs/CONSTITUTION.md` |
| Paridade Matrix | `docs/architecture/R2-ParityMatrix.md` |
| Fitness Functions v2 | `docs/ArchitectureFitnessFunctions.md` |
| GO/NO-GO Checklist | `docs/reviews/R2-GoNoGo-Checklist.md` |
| ADR Index | `docs/ArchitectureDecisionIndex.md` |

---

**Decisão ARB:** RFC-003 **aprovada**. Implementação autorizada após checklist GO/NO-GO completo.
