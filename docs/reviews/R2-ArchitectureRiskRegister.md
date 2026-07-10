# R2 — Registro de Riscos Arquiteturais

**Documento:** `docs/reviews/R2-ArchitectureRiskRegister.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**RFC:** [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md)

---

| ID | Risco | Prob. | Impacto | Mitigação | Fase | Owner | Status |
|----|-------|-------|---------|-----------|------|-------|--------|
| R-R2-001 | Dual-write drift core↔legado | Média | Crítico | ADR-024/025; reconciliation F5 | F1+ | Platform | Mitigado (doc) |
| R-R2-002 | Commands bypass ACL | Alta | Alto | F0.5 wiring; FF-BKG-001/002 | F0.5 | Platform | Aberto (código) |
| R-R2-003 | Scheduling tranca até F3 | Alta | Alto | SchedulingPort F0.5 | F0.5 | Platform | Mitigado (doc) |
| R-R2-004 | Approve chain payment break | Média | Alto | PaymentQueryPort; P08 paridade | F2 | Platform | Mitigado (doc) |
| R-R2-005 | Enforcement block amplo | Baixa | Alto | ADR-033 narrow | F6 | Platform | Mitigado (doc) |
| R-R2-006 | Plugin hook regression | Média | Médio | Flag + fallback inline | F4 | Platform | Mitigado (doc) |
| R-R2-007 | Idempotency gap duplicate bookings | Média | Alto | ADR-031 F1b | F1b | Platform | Mitigado (doc) |
| R-R2-008 | Version conflict approve race | Baixa | Médio | Optimistic lock ADR-031 | F2 | Platform | Mitigado (doc) |
| R-R2-009 | Flag debt acumulada | Média | Médio | ADR-032 lifecycle | F0+ | ARB | Mitigado (doc) |
| R-R2-010 | PMM L2 expectativa errada | Média | Médio | Comunicar 65% R2 | F6 | ARB | Mitigado (doc) |
| R-R2-011 | Event alias sunset delay | Baixa | Baixo | ADR-027 schedule | F1b | Platform | Mitigado (doc) |
| R-R2-012 | Worker vs Resource confusion | Média | Médio | ADR-010 explicit table | F3 | Platform | Mitigado (doc) |
| R-R2-013 | Fitness CI not blocking early | Média | Médio | F5 ERROR gates | F5 | Platform | Planejado |
| R-R2-014 | Canary tenant não definido | Média | Alto | GO/NO-GO item | Pré-F1 | Product | Aberto |
| R-R2-015 | Reschedule legado prolongado | Alta | Baixo | ADR-026 R3 explicit | R3 | Platform | Aceito |

---

## Decisões e trade-offs registrados

| Decisão | Opções | Escolha | Motivo descarte alternativas |
|---------|--------|---------|------------------------------|
| SoT | A/B/C/D | D com Core SoT flag ON | A quebra legado; B impede sunset; C sem projeção quebra UX |
| Transaction | Saga / Single TX | Single TX | Saga prematura monolith |
| Cancel scope | R2 / R3 | R2 F2b | SoT híbrido prolongado inaceitável |
| Frontend SDK | R2 / R3 | R3 | Foco backend platform R2 |
| Enforcement | Global / Narrow | Narrow booking | Global quebra payments/fila |
| Event naming | Big-bang / Alias | Dual-publish alias | Big-bang quebra consumers |

---

## Monitoramento contínuo

| Métrica | Threshold alerta |
|---------|------------------|
| `coreflow.booking.legacy_sync.drift_count` | >0 WARNING |
| `coreflow.fitness.violations` | >0 ERROR |
| `coreflow.booking.paridade.pass_rate` | <100% CRITICAL |
| `coreflow.api.legacy_write_ratio{route=booking}` | Track trend |
