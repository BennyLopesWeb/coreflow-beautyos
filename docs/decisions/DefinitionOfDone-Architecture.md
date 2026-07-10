# Definition of Done — Arquitetural

**Documento:** `docs/decisions/DefinitionOfDone-Architecture.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Autoridade:** `docs/CONSTITUTION.md`

---

## Propósito

Toda sprint CoreFlow só é considerada **concluída** quando todos os critérios abaixo forem atendidos. Isso garante evolução incremental sem degradação arquitetural.

---

## Checklist obrigatório

| # | Critério | Verificação |
|---|----------|-------------|
| 1 | **Código implementado** | PR mergeável; escopo alinhado ao RFC/ADR |
| 2 | **Testes automatizados passando** | `pytest` backend verde; novos testes para comportamento introduzido |
| 3 | **Documentação atualizada** | Sprint doc + docs vivos sincronizados (ver § Arquitetura Viva) |
| 4 | **ADR/RFC vinculados** | `ArchitectureDecisionIndex.md` referencia decisões da sprint |
| 5 | **Rollback documentado** | Sprint doc § Rollback com env vars e revert git |
| 6 | **Feature Flag configurada** | Quando aplicável — default seguro (`false` salvo exceção aprovada) |
| 7 | **Telemetria disponível** | Métricas Prometheus e/ou ArchitectureMetrics para novo comportamento |
| 8 | **Observabilidade validada** | Dashboards/endpoints health quando impacto operacional |
| 9 | **Compatibilidade preservada** | APIs legado e v1 continuam funcionais; paridade tests quando migração |
| 10 | **Constituição respeitada** | Nenhuma violação de `docs/CONSTITUTION.md` |

---

## Arquitetura Viva

Após cada sprint concluída, atualizar:

| Documento | Path |
|-----------|------|
| Architecture Assessment | `docs/ArchitectureAssessment.md` |
| Target Architecture | `docs/architecture/TargetArchitecture.md` |
| Architecture Decision Index | `docs/ArchitectureDecisionIndex.md` |
| Core Meta Model | `docs/CoreMetaModel.md` |
| Roadmap 12M | `docs/roadmap/Roadmap-12M.md` |

---

## Exceções

Exceções a qualquer critério exigem **ADR de exceção** ou aprovação explícita do responsável arquitetural registrada no sprint doc.

---

## Referências

- `docs/decisions/PR-Checklist.md`
- `docs/rfc/RFC-002-CoreEnforcementSunset.md`
- `docs/sprints/R1-F2.md` (primeira sprint com DoD formal)
