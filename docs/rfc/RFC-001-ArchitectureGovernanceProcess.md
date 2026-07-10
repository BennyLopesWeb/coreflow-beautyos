# RFC-001 — Processo de Governança e Documentação Arquitetural

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aprovado |
| **Autor** | Principal Architect (CoreFlow) |
| **Data** | 2026-07-09 |
| **ADR relacionado** | [ADR-003](../adr/ADR-003-GovernanceProcess.md) |

---

## Objetivo

Estabelecer processo obrigatório (RFC → ADR → Aprovação → Fases) para toda evolução da CoreFlow Platform, preservando compatibilidade e qualidade arquitetural.

## Problema

O projeto cresceu rapidamente (CF-0 → CF-25) com entregas técnicas sólidas, porém:

- Decisões espalhadas entre `DOCUMENTACAO.md`, SAB parcial e código
- Risco de refatorações grandes que quebrem legado ou regras de negócio
- Hexagonal/DDD aplicados de forma inconsistente fora de `identity` e `payments`
- Três superfícies API (`/agenda`, `/reservations`, `/v1/*`) sem enforcement pleno

Fonte: `docs/ArchitectureAssessment.md` §1, §25.

## Motivação

- Transformar BeautyOS/trancista em **plataforma SaaS CoreFlow** sem reescrita
- Garantir que cada PR seja reversível, testada e documentada
- Permitir novos produtos (SportsOS, ClinicOS, …) apenas via plugins

## Alternativas

| Alternativa | Prós | Contras |
|-------------|------|---------|
| **A — Governança RFC/ADR (proposta)** | Rastreabilidade, baixo risco, aprovação explícita | Overhead inicial |
| **B — Continuar sprints CF sem RFC** | Velocidade imediata | Dívida arquitetural, decisões implícitas |
| **C — Big-bang rewrite v2** | Arquitetura limpa | Quebra compatibilidade, alto risco — **rejeitado** |

## Impacto

- Novos diretórios em `docs/` (architecture, adr, rfc, roadmap, backlog, …)
- PRs significativos exigem checklist (`docs/decisions/PR-Checklist.md`)
- Implementação de código **bloqueada** até RFC+ADR aprovados por feature

## Compatibilidade

- **100% compatível** — processo documental apenas
- Nenhuma alteração de runtime ou API neste RFC

## Plano de Migração

1. Criar estrutura `docs/` (✅ esta entrega)
2. Publicar `ArchitectureEvolutionPlan.md`, `Backlog.md`, `Roadmap-12M.md`
3. Aprovar ADR-003
4. Aplicar checklist em PRs a partir do próximo sprint

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Burocracia excessiva | RFC só para mudanças arquiteturais; bugfixes/doc typos isentos |
| ADRs desatualizados | Índice em `docs/adr/README.md` |
| Time ignora processo | CI comment template + review gate |

## Rollback

Remover exigência de RFC/ADR; manter docs como referência. Zero impacto em produção.

## Arquivos afetados

| Ação | Path |
|------|------|
| Criado | `docs/architecture/`, `docs/adr/`, `docs/rfc/`, `docs/roadmap/`, … |
| Criado | `docs/ArchitectureEvolutionPlan.md` |
| Criado | `docs/Backlog.md` |
| Atualizado | `docs/README.md` |

## Estimativa

| Fase | Esforço |
|------|---------|
| Documentação inicial | 4–8 h |
| Adoção contínua | ~30 min por feature |

---

**Aguardando aprovação antes de qualquer implementação de código.**
