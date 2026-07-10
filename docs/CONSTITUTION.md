# Constituição CoreFlow Platform

**Documento:** `docs/CONSTITUTION.md`  
**Status:** Imutável — nada no repositório pode contrariá-lo  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Autoridade:** Principal Software Architect

---

## Preâmbulo

A CoreFlow Platform é uma **Plataforma de Desenvolvimento de Sistemas de Gestão** — não um único sistema vertical. Novos produtos (BeautyOS, SportsOS, ClinicOS, …) nascem adicionando **Plugins** sobre o mesmo **Core Framework**.

Esta Constituição prevalece sobre código, PRs, sprints e documentação operacional. Em conflito, a Constituição vence.

---

## I. Princípios Imutáveis

| Princípio | Significado |
|-----------|-------------|
| **API First** | Toda regra de negócio existe na API. Clientes são substituíveis. |
| **AI First** | IA é camada de plataforma, não feature isolada de um vertical. |
| **Domain First** | Modelamos conceitos universais antes de terminologia de plugin. |
| **Hexagonal** | Core isolado; infraestrutura e integrações nas bordas via ports/adapters. |
| **DDD** | Bounded contexts, linguagem ubíqua, eventos de domínio. |
| **SOLID** | Especialmente SRP, DIP e ISP em módulos core. |
| **Event Driven** | Comunicação entre contextos preferencialmente por eventos. |
| **Multi Tenant** | Uma infraestrutura, isolamento lógico por tenant (`company_id`). |
| **Plugin First** | Especialização vertical só via plugins — nunca no core. |
| **Mobile First** | Mobile é experiência primária do profissional; web para operações densas. |
| **Backward Compatibility** | APIs publicadas não quebram sem versionamento e período de transição. |
| **Test First** | Comportamento novo exige teste; paridade antes de sunset legado. |
| **Documentation First** | RFC + ADR + Event Catalog + rollback antes de mudança estrutural. |

---

## II. Princípios de Evolução

### Nunca

- Quebrar API publicada (`/v1/*`, JWT claims, eventos Avro versionados) sem ADR e plano de migração
- Duplicar regra de negócio entre Core, Legado e Plugin
- Acoplar Plugins ao Core (imports de domínio beauty/sports/clinic dentro de `app/modules/` genéricos)
- Acoplar IA ao domínio (ex.: `BeautyAgent` no módulo `ai/` core)
- Acessar infraestrutura diretamente da camada de domínio ou application (SQLAlchemy, Kafka, HTTP externo)
- Remover componente legado sem telemetria de utilização, performance, erros e usuários impactados
- Integrar Core ↔ Legado sem **Anti-Corruption Layer** (ACL)
- Migrar comportamento sem **Feature Flag** documentada
- Implementar mudança arquitetural sem **rollback documentado**

### Sempre

- Usar **Ports** na application layer
- Usar **Adapters** na infrastructure layer
- Publicar **Eventos** de domínio para efeitos colaterais
- Documentar **RFC** (proposta) e **ADR** (decisão)
- Passar integrações Legado → **Adapter** → **Port** → Core
- Proteger migrações com **Feature Flags** (`booking.core.enabled`, etc.)
- Registrar telemetria antes de sunset
- Responder às **Cinco Perguntas** (Artigo IV) antes de aprovar implementação

---

## III. Meta Modelo Universal

O Core opera **somente** sobre conceitos definidos em `docs/CoreMetaModel.md`.

Plugins **especializam terminologia** — nunca entidades core duplicadas.

**Proibido no core:** Tranca, Quadra, Consultório, Agendamento (como conceito de domínio), Fila (como nome de entidade).

**Obrigatório no core:** Worker, Resource, Booking, Catalog, Offering, Customer, Location, Company.

---

## IV. As Cinco Perguntas (obrigatórias)

Toda decisão arquitetural futura **deve** responder:

1. **Essa funcionalidade pertence ao Core ou a um Plugin?**
2. **Ela pode ser reutilizada por outros segmentos?**
3. **Existe um conceito mais genérico que represente essa regra?**
4. **Estamos modelando um negócio específico ou um conceito universal?**
5. **Essa decisão facilita ou dificulta a criação de novos produtos no futuro?**

Se qualquer resposta indicar **acoplamento ao domínio Beauty** (ou outro vertical), a implementação **deve ser revista** antes de aprovação.

---

## V. Processo de Governança

Fluxo obrigatório (RFC-001 aprovado):

```
Análise → RFC → ADR → Aprovação → Plano de Fases → Uma Fase → Testes → Documentação → Próxima Sprint
```

- Uma fase por PR
- PR Checklist: `docs/decisions/PR-Checklist.md`
- Índice de decisões: `docs/ArchitectureDecisionIndex.md`

---

## VI. Strangler Fig e Legado

Coexistência legado + v1 é **temporária** e **controlada**:

- Mapa Legado → Core: `docs/architecture/LegacyToCoreRouteMap.md`
- Enforcement gradual: `warn` → `block` (RFC-002)
- ACL obrigatória em toda ponte Core ↔ Legado
- Nunca dependência direta Core → código legado de domínio (delegação existente deve migrar para ACL)

---

## VII. Referências

| Documento | Path |
|-----------|------|
| Meta Modelo | `docs/CoreMetaModel.md` |
| Visão 2030 | `docs/ArchitectureVision2030.md` |
| Plano de evolução | `docs/ArchitectureEvolutionPlan.md` |
| ADR Index | `docs/ArchitectureDecisionIndex.md` |
| Constituição | **este documento** |

---

*Emendamentos requerem ADR dedicado e aprovação explícita do Principal Architect.*
