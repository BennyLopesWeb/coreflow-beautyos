# R2 — Checklist Executivo GO/NO-GO

**Documento:** `docs/reviews/R2-GoNoGo-Checklist.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Gate:** Obrigatório antes de R2-F1 (primeiro código de domínio)

---

## Arquitetura

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| A1 | RFC-003 aprovado ARB | `docs/rfc/RFC-003-CoreDomainConsolidation.md` | ✅ |
| A2 | ADR-009–011 aceitos | `docs/adr/ADR-009` … `011` | ✅ |
| A3 | ADR-024–033 aceitos | `docs/adr/ADR-024` … `033` | ✅ |
| A4 | Dual-write SoT definido (Core flag ON) | ADR-024 | ✅ |
| A5 | Transaction boundaries definidas | ADR-025 | ✅ |
| A6 | Worker ≠ Resource definido | ADR-010 | ✅ |
| A7 | Enforcement scope narrow | ADR-033 | ✅ |
| A8 | R2-ExecutionPlan v4 aprovado | `docs/R2-ExecutionPlan.md` | ✅ |

## Documentação

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| D1 | Docs estratégicos v3 (20 pilares) | `PlatformStrategyIndex.md` | ✅ |
| D2 | Paridade matrix ≥12 cenários | `R2-ParityMatrix.md` | ✅ |
| D3 | Event migration plan | ADR-027 | ✅ |
| D4 | Flag lifecycle registry | ADR-032 | ✅ |
| D5 | Risk register publicado | `R2-ArchitectureRiskRegister.md` | ✅ |

## Governança

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| G1 | Processo RFC→ADR→Fase documentado | RFC-001, ADR-003 | ✅ |
| G2 | 1 PR = 1 fase acordado | R2-ExecutionPlan v4 | ✅ |
| G3 | Rollback por fase documentado | RFC-003 §8, sprint template | ✅ |
| G4 | Architecture Board approval | Registro abaixo | ☐ Pendente |

## Qualidade

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| Q1 | DoD arquitetural vigente | `DefinitionOfDone-Architecture.md` | ✅ |
| Q2 | Fitness functions v2 por fase | `ArchitectureFitnessFunctions.md` | ✅ |
| Q3 | Coupling baseline ≤4 | R1-F2 metrics | ✅ |
| Q4 | Test count baseline ≥268 | CI | ✅ |

## Testes

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| T1 | Paridade test plan definido | R2-ParityMatrix.md | ✅ |
| T2 | CF-8 patterns referenciados | existing tests | ✅ |
| T3 | Contract test plan (OpenAPI) | F5 scope | ☐ F5 |

## Paridade

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| P1 | 12 cenários documentados | R2-ParityMatrix.md | ✅ |
| P2 | Gate por fase definido | R2-ParityMatrix §gate | ✅ |

## Performance

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| PF1 | Single TX dual-write spec | ADR-025 | ✅ |
| PF2 | Idempotency dedupe | ADR-031 | ✅ |
| PF3 | N+1 policy repositories | ADR-030 | ✅ |

## Observabilidade

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| O1 | Reconciliation metrics defined | ADR-024 | ✅ |
| O2 | OTEL spans planned F5 | R2-F5 | ☐ F5 |
| O3 | correlation_id in events | ADR-027, F1b | ☐ F1b |

## Segurança

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| S1 | Tenant isolation INV-B1 | ADR-009 | ✅ |
| S2 | RBAC unchanged R2 | existing | ✅ |
| S3 | No PII in event names | FF-EVT-004 | ✅ |

## Feature Flags

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| F1 | All R2 flags registered | ADR-032 | ✅ |
| F2 | Default false documented | RFC-003 §6 | ✅ |
| F3 | Sunset dates defined | ADR-032 | ✅ |

## Rollback

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| RB1 | Flag rollback <5 min | RFC-003 §8 | ✅ |
| RB2 | R1-F2 rollback tested | R1-F2 sprint doc | ✅ |
| RB3 | Per-phase revert procedure | R2-ExecutionPlan | ✅ |

## Canary

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| C1 | Staging tenant `company_id` identificado | Sprint F1 doc | ☐ Pendente |
| C2 | Prod canary plan 1→100% | RFC-003 §5 | ✅ |

## CI/CD

| # | Critério | Evidência | Status |
|---|----------|-----------|--------|
| CI1 | Fitness scripts baseline F0 | F0 deliverable | ☐ F0 impl |
| CI2 | ERROR block plan F5 | ArchitectureFitnessFunctions | ☐ F5 |

## ADR / RFC

| # | Critério | Status |
|---|----------|--------|
| RF1 | RFC-003 | ✅ |
| RF2 | ADR-009–033 | ✅ |
| RF3 | ArchitectureDecisionIndex updated | ✅ |

## Aprovação Architecture Board

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Principal Architect | — | ☐ | |
| Staff Engineer | — | ☐ | |
| Product Owner | — | ☐ | |

---

## Veredito

| Resultado | Condição |
|-----------|----------|
| **GO** | Governança consolidada; R2-F0.5 ✅; R2-F1 após DoR operacional |

### Autorizado agora

- ✅ R2-F0.5 concluído
- ✅ Redação sprint doc R2-F1

### Requer antes de merge R2-F1

- ☐ G4 Architecture Board approval
- ☐ C1 Canary tenant identificado
- ☐ Sprint doc R2-F1 publicado

---

**Referência:** Parecer completo em `docs/reviews/R2-ARB-FinalVerdict.md`
