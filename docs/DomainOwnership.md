# CoreFlow — Domain Ownership

**Documento:** `docs/DomainOwnership.md`  
**Versão:** 1.0 · **Data:** 2026-07-09  
**Status:** Normativo — escalável para multi-time  
**Relacionado:** `docs/DomainRegistry.md`, `docs/BoundedContexts.md`

---

## Propósito

Define **ownership** por bounded context — responsável por ADRs, evolução de API, paridade e operação — mesmo quando hoje existe um único time.

---

## Matriz de ownership

| Bounded Context | Owner Team | Tech Lead | ADRs principais | API prefix | Escalation |
|-----------------|------------|-----------|-----------------|------------|------------|
| **Platform / Core** | Platform Team | Principal Architect | ADR-005, ADR-030 | `/v1/platform/*` | ARB |
| **Booking** | Platform Team | Staff Engineer | ADR-009, ADR-024–026 | `/v1/bookings` | ARB |
| **Scheduling** | Platform Team | Staff Engineer | ADR-008, ADR-029 | `/v1/scheduling` | ARB |
| **Resource** | Platform Team | Staff Engineer | ADR-010, ADR-007 | `/v1/resources` | ARB |
| **Catalog** | Platform Team | Backend Lead | ADR-030 | `/v1/catalogs` | Platform Lead |
| **Customer** | Platform Team | Backend Lead | ADR-030 | `/v1/customers` | Platform Lead |
| **Payments** | Financial Platform | Backend Lead | ADR-028 | `/v1/payments` | Product + ARB |
| **Orders / Invoices** | Financial Platform | Backend Lead | — | `/v1/orders`, `/v1/invoices` | Product |
| **Waitlist** | Platform Team | Backend Lead | — | `/v1/waitlist` | Platform Lead |
| **Workflow** | Platform Team | Backend Lead | — | `/v1/workflows` | Platform Lead |
| **Plugins / Marketplace** | Marketplace Team | Staff Engineer | ADR-006, ADR-011 | `/v1/plugins` | ARB |
| **Identity / Tenant** | Platform Team | Security Lead | — | `/companies`, auth | Security |
| **Observability** | Platform Team | SRE Lead | — | `/v1/platform/health` | SRE |
| **Mobile / BFF** | Mobile Team | Mobile Lead | `MobilePlatform.md` | BFF routes | Mobile Lead |
| **AI / Agents** | AI Platform | AI Lead | ADR-012 (R4) | `/v1/ai` | ARB |

---

## Responsabilidades do Owner

| Responsabilidade | Detalhe |
|------------------|---------|
| **ADRs** | Propor RFC/ADR para mudanças estruturais no contexto |
| **API** | Manter OpenAPI, versionamento, deprecation |
| **Paridade** | Cenários de paridade quando migra legado |
| **Fitness** | Garantir FF do contexto passam na fase |
| **Incidentes** | P1/P2 no domínio — runbook e rollback |
| **On-call** | Escalation path documentado |

---

## Contextos compartilhados

| Fronteira | Owner primário | Owner secundário | Regra |
|-----------|----------------|------------------|-------|
| Booking ↔ Payments | Booking | Financial | ADR-028 — PaymentQueryPort only |
| Booking ↔ Scheduling | Booking | Scheduling | SchedulingPort / ResourcePort |
| Core ↔ Plugins | Platform | Marketplace | Hooks typed; zero import cruzado |
| Core ↔ Legado | Platform | — | ACL only (`shared/acl/`) |

---

## Evolução multi-time (R3+)

Quando novos times forem criados:

1. Atualizar esta matriz (PR + ARB ack)
2. Registrar em `ArchitectureDecisionLog.md`
3. Atualizar `CODEOWNERS` (quando existir)
4. Domain Registry (`DomainRegistry.md`) status por contexto

---

## Referências

- `docs/DomainRegistry.md`
- `docs/BoundedContexts.md`
- `docs/EcosystemStrategy.md`
