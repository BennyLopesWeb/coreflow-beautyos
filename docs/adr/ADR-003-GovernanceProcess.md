# ADR-003 — Processo de Governança Arquitetural

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-001](../rfc/RFC-001-ArchitectureGovernanceProcess.md) |

## Contexto

CoreFlow evolui de produto vertical (trancista) para plataforma multi-plugin. CF-0→CF-25 entregaram infraestrutura transversal; auditoria (`ArchitectureAssessment.md`) identificou gaps DDD/Hexagonal e API tripla.

## Problema

Sem processo formal, há risco de:

- Refatorações grandes e irreversíveis
- Decisões implícitas no código
- Violação de princípios (API First, Domain First)
- PRs sem testes ou rollback

## Decisão

Adotar fluxo **obrigatório** para mudanças arquiteturais:

```
Análise → RFC → ADR → Aprovação → Plano de Fases → Uma Fase → Testes → Doc
```

Regras:

1. **Nunca** apagar funcionalidades; **nunca** big-bang rewrite
2. RFC em `docs/rfc/`; ADR em `docs/adr/`
3. Implementação **bloqueada** até aprovação explícita
4. Uma fase por PR; fases reversíveis
5. PR checklist em `docs/decisions/PR-Checklist.md`

Bugfixes triviais e docs typos **isentos** de RFC.

## Consequências

- Overhead ~30 min/feature arquitetural
- Rastreabilidade completa de decisões
- Onboarding facilitado via `ArchitectureEvolutionPlan.md`

## Benefícios

- Compatibilidade preservada
- Evolução incremental alinhada ao Strangler Fig (ADR-001, ADR-004)
- Guardião arquitetural explícito (role Principal Architect)

## Trade-offs

| Pró | Contra |
|-----|--------|
| Qualidade previsível | Velocidade inicial menor |
| Rollback claro | Mais arquivos para manter |

## Alternativas descartadas

- **Sprints CF sem governança** — levou a decisões implícitas
- **Microsserviços prematuros** — viola Modular Monolith

## Referências

- `docs/ArchitectureAssessment.md`
- `BEAUTYOS_BLUEPRINT.md` §4
- `docs/rfc/RFC-001-ArchitectureGovernanceProcess.md`
