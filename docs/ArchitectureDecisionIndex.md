# CoreFlow — Architecture Decision Index

**Última atualização:** 2026-07-09 (R2 consolidation — RFC-003 + ADR-009–033)  
**Autoridade:** `docs/CONSTITUTION.md`

---

## Índice de ADRs

| ADR | Título | Status | Data | Impacto | Dependências |
|-----|--------|--------|------|---------|--------------|
| [ADR-001](../06-ADR/ADR001-metamodel.md) | Metamodelo Genérico CoreFlow | ✅ Aceito | 2026-07-09 | Alto | — |
| [ADR-002](../06-ADR/ADR002-beauty-plugin.md) | Beauty como Plugin Piloto | ✅ Aceito | 2026-07-09 | Alto | ADR-001 |
| [ADR-003](./ADR-003-GovernanceProcess.md) | Processo de Governança | ✅ Aceito | 2026-07-09 | Alto | RFC-001 |
| [ADR-004](./ADR-004-IncrementalEvolutionStrategy.md) | Evolução Incremental Strangler Fig | ✅ Aceito | 2026-07-09 | Alto | ADR-001, RFC-002 |
| [ADR-005](./ADR-005-CoreFramework.md) | Core Framework — limites | ✅ Aceito | 2026-07-09 | Alto | ADR-001 |
| [ADR-006](./ADR-006-PluginArchitecture.md) | Plugin Architecture | ✅ Aceito | 2026-07-09 | Alto | ADR-005 |
| [ADR-007](./ADR-007-ResourceEngine.md) | Resource Engine | ✅ Aceito | 2026-07-09 | Médio | ADR-001, ADR-005 |
| [ADR-008](./ADR-008-SchedulingEngine.md) | Scheduling Engine | ✅ Aceito | 2026-07-09 | Médio | ADR-007 |
| [ADR-009](./adr/ADR-009-BookingDomainPure.md) | Booking Domain Pure | ✅ Aceito | 2026-07-09 | **Crítico** | RFC-003 |
| [ADR-010](./adr/ADR-010-ResourceEngine.md) | Resource Engine v1 Meta Model | ✅ Aceito | 2026-07-09 | **Crítico** | ADR-007, RFC-003 |
| [ADR-011](./adr/ADR-011-PluginHookArchitecture.md) | Plugin Hook Architecture | ✅ Aceito | 2026-07-09 | **Crítico** | ADR-006, RFC-003 |
| [ADR-024](./adr/ADR-024-DualWriteStrategy.md) | Dual Write & Source of Truth | ✅ Aceito | 2026-07-09 | **Crítico** | ADR-004, RFC-003 |
| [ADR-025](./adr/ADR-025-TransactionBoundaries.md) | Transaction Boundaries Booking | ✅ Aceito | 2026-07-09 | **Crítico** | ADR-024 |
| [ADR-026](./adr/ADR-026-BookingStateMachine.md) | Booking State Machine | ✅ Aceito | 2026-07-09 | Alto | ADR-009 |
| [ADR-027](./adr/ADR-027-ReservationToBookingMigration.md) | Reservation → Booking Events | ✅ Aceito | 2026-07-09 | Alto | ADR-009 |
| [ADR-028](./adr/ADR-028-PaymentBoundary.md) | Payment Boundary | ✅ Aceito | 2026-07-09 | Alto | ADR-009 |
| [ADR-029](./adr/ADR-029-SchedulingPortEvolution.md) | Scheduling Port Evolution | ✅ Aceito | 2026-07-09 | Alto | ADR-010 |
| [ADR-030](./adr/ADR-030-RepositoryACLStrategy.md) | Repository + ACL Strategy | ✅ Aceito | 2026-07-09 | Alto | ADR-009 |
| [ADR-031](./adr/ADR-031-IdempotencyConcurrency.md) | Idempotency & Concurrency | ✅ Aceito | 2026-07-09 | Alto | ADR-024 |
| [ADR-032](./adr/ADR-032-FeatureFlagLifecycle.md) | Feature Flag Lifecycle R2 | ✅ Aceito | 2026-07-09 | Médio | RFC-003 |
| [ADR-033](./adr/ADR-033-EnforcementBlockScope.md) | Enforcement Block Scope | ✅ Aceito | 2026-07-09 | Alto | RFC-002, ADR-024 |

**Legenda status:** ✅ Aceito · ⏳ Proposto · ❌ Rejeitado · 🔄 Substituído

---

## Índice de RFCs

| RFC | Título | Status | Data | ADR | Impacto |
|-----|--------|--------|------|-----|---------|
| [RFC-001](../rfc/RFC-001-ArchitectureGovernanceProcess.md) | Governança Arquitetural | ✅ Aprovado | 2026-07-09 | ADR-003 | Processo |
| [RFC-002](../rfc/RFC-002-CoreEnforcementSunset.md) | Core Enforcement + Sunset | ✅ Aprovado c/ ajustes | 2026-07-09 | ADR-004, ADR-033 | API migration |
| [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) | Core Domain Consolidation R2 | ✅ Aprovado ARB | 2026-07-09 | ADR-009–033 | **Release 2** |

---

## Releases vinculados

| Release | ADRs / RFCs principais |
|---------|------------------------|
| R1 (jul-set/2026) | RFC-001/002, ADR-003–008, R1-F1, R1-F2 |
| **R2 (out-dez/2026)** | **RFC-003, ADR-009–011, ADR-024–033**, R2-ExecutionPlan v4 |
| R3 (jan-mar/2027) | RFC-004, ADR-014, Integration Hub, PMM L2 exit |

---

## Próximos RFCs planejados

| RFC | Tópico | Release |
|-----|--------|---------|
| RFC-004 | Integration Hub | R3 |
| RFC-009 | Event Envelope Standard (full) | R2-F1b |
| RFC-005–011 | Ver índice anterior | R3–R5 |

---

## R2 Governance Package

| Documento | Path |
|-----------|------|
| Execution Plan v4 | `docs/R2-ExecutionPlan.md` |
| Paridade Matrix | `docs/architecture/R2-ParityMatrix.md` |
| GO/NO-GO Checklist | `docs/reviews/R2-GoNoGo-Checklist.md` |
| ARB Final Verdict | `docs/reviews/R2-ARB-FinalVerdict.md` |
| Risk Register | `docs/reviews/R2-ArchitectureRiskRegister.md` |
| Fitness Functions v2 | `docs/ArchitectureFitnessFunctions.md` |
| Architecture Principles | `docs/ArchitecturePrinciples.md` |
| Release Governance | `docs/ReleaseGovernance.md` |
| Definition of Ready | `docs/decisions/DefinitionOfReady-Architecture.md` |
| ADR Lifecycle | `docs/decisions/ADR-Lifecycle.md` |
| Decision Log | `docs/ArchitectureDecisionLog.md` |
| Domain Ownership | `docs/DomainOwnership.md` |
| Architecture Compliance | `docs/reviews/ArchitectureCompliance.md` |
| Sprint R2-F0.5 | `docs/sprints/R2-F0.5.md` |
| Sprint R2-F1 | `docs/sprints/R2-F1.md` |
| Sprint R2-F1b | `docs/sprints/R2-F1b.md` |
| Gate Review F1b | `docs/reviews/R2-F1b-GateReview.md` |
| Sprint R2-F2 | `docs/sprints/R2-F2.md` |
| Staging checklist F1 | `docs/checklists/R2-F1-StagingValidation.md` |
| Sprint Template | `docs/templates/SprintTemplate.md` |

---

## Como adicionar decisão

1. Abrir RFC em `docs/rfc/`
2. Após aprovação ARB, criar ADR em `docs/adr/`
3. Atualizar **este índice**
4. Referenciar em PR e sprint doc
