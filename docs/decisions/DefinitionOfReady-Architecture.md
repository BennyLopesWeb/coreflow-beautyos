# Definition of Ready — Arquitetural (DoR)

**Documento:** `docs/decisions/DefinitionOfReady-Architecture.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Autoridade:** `docs/CONSTITUTION.md`, `docs/ReleaseGovernance.md`  
**Complementa:** `DefinitionOfDone-Architecture.md`

---

## Propósito

Uma fase **não inicia implementação** até que todos os critérios DoR abaixo estejam atendidos. Evita iniciar trabalho sem ADRs, ambientes ou rollback.

---

## DoR — Release (uma vez por release)

| # | Critério | Verificação |
|---|----------|-------------|
| R1 | RFC da release aprovada | Status ✅ no índice |
| R2 | ADRs da release aceitos | `ArchitectureDecisionIndex.md` |
| R3 | Execution Plan aprovado | Versão documentada |
| R4 | Paridade matrix publicada | Se release migra legado |
| R5 | Fitness gates por fase definidos | `ArchitectureFitnessFunctions.md` |
| R6 | GO/NO-GO checklist | Stakeholder + ARB quando aplicável |
| R7 | Release anterior DoD completo | Sprint docs ✅ |

---

## DoR — Fase (cada F0, F0.5, F1…)

| # | Critério | Verificação |
|---|----------|-------------|
| F1 | **Sprint doc criado** | `docs/sprints/R{N}-F{M}.md` com objetivo, escopo, rollback |
| F2 | **Fase anterior DoD ✅** | Sequência respeitada — proibido pular |
| F3 | **ADRs da fase identificados** | Listados no sprint doc |
| F4 | **Escopo OUT explícito** | O que NÃO será feito nesta fase |
| F5 | **Arquivos afetados mapeados** | Lista no sprint doc |
| F6 | **Estratégia rollback** | Env vars + git revert |
| F7 | **Testes planejados** | Unit, integração, paridade, fitness |
| F8 | **Feature flags** | Default documentado (se aplicável) |
| F9 | **Ambiente staging** | Disponível para validação |
| F10 | **Canary tenant** | `company_id` documentado (quando flag ON em prod) |
| F11 | **Sem ambiguidade arquitetural** | Nenhum item aberto no ARB para esta fase |
| F12 | **Métricas/telemetria** | Planejadas se fase expõe novo path |

---

## DoR — R2-F0.5 (exemplo)

| Critério | Status |
|----------|--------|
| R2-F0 docs ✅ | ✅ |
| RFC-003, ADR-009, 029, 030 | ✅ |
| Sprint doc R2-F0.5 | ✅ (criado antes de código) |
| Escopo: ACL only, sem domain puro | ✅ |
| Rollback: git revert | ✅ |

---

## DoR — Pull Request (início do dev)

| # | Critério |
|---|----------|
| P1 | Branch nomeada por fase (`r2-f0.5-acl-wiring`) |
| P2 | Sprint doc referenciado na descrição |
| P3 | Nenhuma funcionalidade da próxima fase incluída |

---

## Exceções

Exceção a qualquer critério DoR exige **aprovação ARB registrada** no sprint doc com data e motivo.

---

## Referências

- `docs/ReleaseGovernance.md`
- `docs/decisions/DefinitionOfDone-Architecture.md`
- `docs/R2-ExecutionPlan.md`
- `docs/reviews/R2-GoNoGo-Checklist.md`
