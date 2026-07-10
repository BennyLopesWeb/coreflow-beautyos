# Architecture Compliance Review

**Documento:** `docs/reviews/ArchitectureCompliance.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Frequência:** **A cada release** (gate PMM + pós-merge última fase)  
**Responsável:** Principal Architect + Platform Team  
**Relacionado:** `docs/ArchitectureFitnessFunctions.md`, `docs/PlatformMaturityModel.md`

---

## Propósito

Health check arquitetural recorrente — verifica conformidade com Constituição, ADRs vigentes, fitness functions e fronteiras de domínio. Complementa testes automatizados com revisão qualitativa.

---

## Quando executar

| Gatilho | Obrigatório |
|---------|-------------|
| Fim de cada Release (ex.: R2-F6) | ✅ |
| Quarterly (PMM review) | ✅ |
| Antes de GO para próxima Release | ✅ |
| Após incidente P1 arquitetural | ✅ |

---

## Checklist de compliance

### 1. Constituição

| # | Critério | R2 baseline | R{N} atual | Pass |
|---|----------|-------------|------------|------|
| C1 | Zero violação Artigo II (Nunca/Sempre) | ✅ | | ☐ |
| C2 | Meta model respeitado (Worker ≠ Resource) | ✅ ADR-010 | | ☐ |
| C3 | Plugin First — zero beauty em `modules/` | F4 gate | | ☐ |
| C4 | API First — rotas `/v1/*` canônicas | Parcial | | ☐ |
| C5 | Documentação First — RFC/ADR antes de structural | ✅ | | ☐ |

### 2. ADRs

| # | Critério | Verificação | Pass |
|---|----------|-------------|------|
| A1 | Índice sincronizado com repo | `ArchitectureDecisionIndex.md` | ☐ |
| A2 | Nenhum ADR Accepted editado in-place | `ADR-Lifecycle.md` | ☐ |
| A3 | Decision Log atualizado | `ArchitectureDecisionLog.md` | ☐ |
| A4 | ADRs da release todos Accepted | RFC-003 + ADR-009–033 R2 | ☐ |
| A5 | Superseded ADRs referenciam successor | | ☐ |

### 3. Fitness Functions

| # | Critério | Threshold R2 | Atual | Pass |
|---|----------|--------------|-------|------|
| F1 | pytest count | ≥300 (F5) | 271 | ☐ |
| F2 | identified couplings | ≤3 (F5) | | ☐ |
| F3 | FF-BKG-001 ERROR | F2+ | WARN F0.5 | ☐ |
| F4 | FF-IMP-003 (no ReservationService in commands) | ERROR F2 | ✅ F0.5 | ☐ |
| F5 | CI fitness ERROR on critical | F5 | Local only | ☐ |
| F6 | Paridade booking | 12/12 F6 | 0 impl | ☐ |

### 4. Ports & Hexagonal

| # | Critério | Pass |
|---|----------|------|
| P1 | Commands → Port → Adapter → Legacy (booking) | ✅ F0.5 | ☐ |
| P2 | Legado bridge only `shared/acl/` | ☐ |
| P3 | Domain sem SQLAlchemy/Kafka imports | ☐ |
| P4 | 6+ modules com infrastructure/ (target R2) | ☐ |
| P5 | Repository pattern ADR-030 nos contextos da fase | ☐ |

### 5. Dependencies & Cycles

| # | Critério | Pass |
|---|----------|------|
| D1 | Zero cycles `app/modules/*` | ☐ |
| D2 | `shared/` não importa `modules/` | ☐ |
| D3 | Plugins não importam legado models | ☐ |
| D4 | Cross-context domain imports = 0 | ☐ |

### 6. Plugin isolation

| # | Critério | Pass |
|---|----------|------|
| PL1 | Hooks via manifest only | ☐ |
| PL2 | BeautyAgent em `plugins/beauty/` (F4) | ☐ |
| PL3 | Zero plugin import plugin | ☐ |
| PL4 | Manifest schema valid | ☐ |

### 7. Event & Dual-write (R2+)

| # | Critério | Pass |
|---|----------|------|
| E1 | Core SoT when flag ON (ADR-024) | ☐ |
| E2 | TX order ADR-025 | ☐ |
| E3 | `booking.*` + alias `reservation.*` (ADR-027) | ☐ |
| E4 | Reconciliation drift metric (F5) | ☐ |

### 8. Observabilidade

| # | Critério | Pass |
|---|----------|------|
| O1 | Platform health API operacional | ✅ | ☐ |
| O2 | ACL invocations tracked | ✅ | ☐ |
| O3 | OTEL spans core booking path (F5) | ☐ |

---

## Resultado da review

| Release | Data | Reviewer | Score | Veredito |
|---------|------|----------|-------|----------|
| R1 | 2026-07-09 | ARB | Pass | ✅ Foundation complete |
| R2 | _pendente F6_ | | | ☐ |

### Escala de score

| Score | Significado |
|-------|-------------|
| **Pass** | Todos itens críticos ✅; WARN documentados com backlog |
| **Pass w/ debt** | Pass com tech debt P2 registrado |
| **Fail** | Qualquer item crítico ❌ — block próxima release |

---

## Ações pós-review

1. Registrar resultado em `ArchitectureDecisionLog.md`
2. Atualizar `ArchitectureAssessment.md` appendix
3. Abrir backlog items para WARN/Fail
4. PMM gate review (`PlatformMaturityModel.md`)

---

## R3 — Oportunidade registrada (não bloqueio R2)

Refinar camadas Application:

```
Application Service (orquestra ports, TX, DTOs)
    ↓
Domain Service (regra multi-aggregate, raro)
    ↓
Aggregate (invariantes, transições)
    ↓
Repository Port
```

Propor **ADR-034** em R3 prep se implementação F1–F2 misturar responsabilidades.

---

## Referências

- `docs/CONSTITUTION.md`
- `docs/ArchitectureFitnessFunctions.md`
- `docs/decisions/ADR-Lifecycle.md`
- `docs/DomainOwnership.md`
