# CoreFlow — Architecture Principles

**Documento:** `docs/ArchitecturePrinciples.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Autoridade:** Derivado de `docs/CONSTITUTION.md` — não contradiz a Constituição  
**Audiência:** Desenvolvedores, revisores, agentes de IA

---

## Propósito

Dez princípios imutáveis e acionáveis derivados da Constituição. Use como filtro rápido antes de qualquer PR ou decisão técnica.

---

## Princípios

### P1 — Core genérico, Plugin específico

Regras universais vivem no Core; terminologia e especialização vivem em Plugins. Se a regra menciona cadeira, tranca ou quadra no core → **pare e mova para plugin**.

### P2 — API First

Toda capacidade de negócio existe na API `/v1/*`. Clientes (web, mobile, integrações) são substituíveis. Nunca implementar lógica exclusiva no frontend que não exista na API.

### P3 — Domain First (DDD)

Modelar bounded contexts com linguagem ubíqua em inglês no código. Aggregates protegem invariantes. Comunicação entre contextos via ports ou eventos — nunca import de domain alheio.

### P4 — Hexagonal (Ports & Adapters)

Application depende de Protocols; infrastructure implementa adapters. Domain não conhece SQLAlchemy, HTTP, Kafka ou legado. Legado **sempre** via ACL em `shared/acl/`.

### P5 — Event Driven

Efeitos colaterais cross-context preferencialmente por eventos de domínio + outbox. Eventos nomeados `{aggregate}.{action}`. Payload inclui `company_id` quando tenant-scoped.

### P6 — Strangler Fig incremental

Migrar comportamento com feature flags, paridade tests e rollback documentado. Nunca big-bang. Nunca remover legado sem telemetria e block gate.

### P7 — Backward Compatibility

APIs publicadas `/v1/*` não quebram sem versionamento e ADR. Eventos Avro evoluem de forma aditiva. Aliases temporários (`reservation.*`) seguem ADR-027 até sunset.

### P8 — Multi-Tenant by design

Toda entidade tenant-scoped tem `company_id`. Toda query filtra tenant. Nunca expor dados cross-tenant.

### P9 — Test & Paridade antes de Sunset

Comportamento novo exige testes. Migração legado→core exige paridade documentada. Enforcement block só após paridade 100% no escopo narrow.

### P10 — Documentation & Governance First

Mudança estrutural exige RFC → ADR → fase → PR. Uma fase por PR. Se não está nos ADRs aprovados, **pare e solicite decisão do ARB**.

### P11 — Worker ≠ Resource

Worker executa serviço; Resource é reservável. Nunca modelar profissional como Resource (ADR-010).

### P12 — Source of Truth explícito

Com `FEATURE_BOOKING_CORE_ENABLED=true`, Core é SoT; legado é projeção (ADR-024). Nunca inverter sem ADR.

### P13 — Menor mudança possível

Escolher o diff mínimo que resolve a fase atual. Não antecipar R3–R6. Refactoring só se reduz acoplamento da fase sem alterar comportamento.

### P14 — Observabilidade não é opcional

Métricas, logs estruturados e telemetria ACL acompanham toda migração. Drift dual-write deve ser detectável (reconciliation).

### P15 — Fitness Functions guardam a arquitetura

Violações da Constituição ou ADRs devem falhar CI (ERROR). WARN vira ERROR conforme calendário da release.

---

## Aplicação rápida (checklist PR)

1. Pertence ao Core ou Plugin? (P1)
2. Passa por port/adapter? (P4)
3. Tem flag se migração? (P6)
4. Tem teste + paridade se aplicável? (P9)
5. ADR/RFC referenciado? (P10)

---

## Referências

| Documento | Path |
|-----------|------|
| Constituição | `docs/CONSTITUTION.md` |
| Release Governance | `docs/ReleaseGovernance.md` |
| Definition of Ready | `docs/decisions/DefinitionOfReady-Architecture.md` |
| Definition of Done | `docs/decisions/DefinitionOfDone-Architecture.md` |
