# Sprint Template — CoreFlow Platform

**Documento:** `docs/templates/SprintTemplate.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Uso:** Copiar para `docs/sprints/R{N}-F{M}.md` no início de cada fase  
**Governança:** [ReleaseGovernance.md](../ReleaseGovernance.md) · [DefinitionOfReady-Architecture.md](../decisions/DefinitionOfReady-Architecture.md)

---

## Instruções

1. Duplicar este template → `docs/sprints/R2-F2.md` (exemplo)  
2. Preencher **antes** de qualquer código (DoR)  
3. Manter como **referência única** da sprint  
4. Atualizar §17 ao concluir (DoD)  
5. Registrar conclusão em `ArchitectureDecisionLog.md`

---

# Release {N} — Sprint R{N}-F{M}

**Documento operacional único desta sprint.**

---

## 1. Identificação da Sprint

| Campo | Valor |
|-------|-------|
| **Sprint** | R{N}-F{M} |
| **Versão** | `{semver}-r{n}-f{m}` |
| **Status** | ⏳ Ready (após DoR) / 🔄 Em execução / ✅ Concluído |
| **Release** | R{N} — {nome release} |
| **Fase anterior** | R{N}-F{M-1} — {status} |
| **Próxima fase** | R{N}-F{M+1} — {nome} |
| **Owner** | {Team} — [DomainOwnership.md](../DomainOwnership.md) |
| **Objetivo estratégico** | {uma frase — outcome de negócio/arquitetura} |

---

## 2. Objetivo

{Descrever resultado esperado em 2–4 frases. Incluir feature flags e ADRs-chave se aplicável.}

**Resultado mensurável:** {métricas / paridade / gates objetivos}

---

## 3. Escopo IN

| # | Entrega | Detalhe |
|---|---------|---------|
| 1 | | |
| 2 | | |

---

## 4. Escopo OUT

**Proibido nesta sprint** — scope creep → parar → ARB.

| Item | Fase correta |
|------|--------------|
| | R{N}-F{X} |

---

## 5. Pré-requisitos (DoR)

| # | Critério | Status |
|---|----------|--------|
| D1 | Fase anterior DoD ✅ | ☐ |
| D2 | RFC/ADR necessários Accepted | ☐ |
| D3 | GO ARB / stakeholder | ☐ |
| D4 | Canary tenant (se flag) | ☐ |
| D5 | Staging disponível | ☐ |
| D6 | Este sprint doc aprovado | ☐ |
| D7 | Baseline testes verde | ☐ |

**Regra:** DoR incompleto → **não iniciar implementação**.

---

## 6. ADRs obrigatórios (resumo operacional)

| ADR | Aplicação nesta sprint |
|-----|------------------------|
| [ADR-XXX](../adr/ADR-XXX.md) | |

---

## 7. Fluxo aprovado

```
{diagrama ASCII ou descrição passo a passo}
```

---

## 8. Arquivos previstos

| Arquivo | Ação | Notas |
|---------|------|-------|
| | Novo / Alterar | |

---

## 9. Feature Flags

| Chave pública | Env var | Inicial | Esperado pós-sprint | Rollback |
|---------------|---------|---------|---------------------|----------|
| | | `false` | | |

### Rollback operacional

```bash
# Comandos exatos
```

---

## 10. Eventos

| Evento | Producer | Alias | Obrigatório | Payload mínimo |
|--------|----------|-------|-------------|----------------|
| | | | ☐ | |

---

## 11. Testes obrigatórios

### Unit

| Área | Casos |
|------|-------|
| | |

### Integration

| Área | Casos |
|------|-------|
| | |

### Paridade

| ID | Cenário | Gate merge |
|----|---------|------------|
| | | ☐ |

---

## 12. Fitness Functions

| ID | Regra | Fase | Ação |
|----|-------|------|------|
| | | WARN/ERROR | |

---

## 13. Métricas (observabilidade)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| | Counter/Histogram | |

---

## 14. Rollback

### Gatilhos

| Gatilho | Ação |
|---------|------|
| | |

### Procedimento completo

1.  
2.  

---

## 15. Critério de Conclusão (DoD)

| # | Critério | ☐ |
|---|----------|---|
| 1 | Código mergeado — escopo §3 only | |
| 2 | pytest verde | |
| 3 | Paridade gate | |
| 4 | Fitness pass | |
| 5 | Métricas/telemetria | |
| 6 | Rollback testado | |
| 7 | Sprint doc + Decision Log | |
| 8 | Release notes / APP_VERSION | |

---

## 16. Critério de GO para {próxima fase}

| # | Gate |
|---|------|
| G1 | |
| G2 | DoD desta sprint completo |

---

## 17. Lições aprendidas

_Preencher ao concluir._

| Data | Lição | Ação follow-up |
|------|-------|----------------|
| | | |

---

## Referências rápidas

| Documento | Path |
|-----------|------|
| Execution Plan | [R{N}-ExecutionPlan.md](../R{N}-ExecutionPlan.md) |
| Template | [SprintTemplate.md](./SprintTemplate.md) |
| DoR / DoD | [DefinitionOfReady](../decisions/DefinitionOfReady-Architecture.md) · [DefinitionOfDone](../decisions/DefinitionOfDone-Architecture.md) |

---

**Última atualização:** {YYYY-MM-DD} · **Status:** {Ready / Em execução / Concluído}

---

## Exemplo preenchido

Ver [R2-F1.md](../sprints/R2-F1.md) · [R2-F0.5.md](../sprints/R2-F0.5.md)
