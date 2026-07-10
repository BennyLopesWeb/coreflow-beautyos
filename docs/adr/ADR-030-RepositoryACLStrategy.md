# ADR-030 — Repository + ACL Strategy

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-009, ADR-011 |

---

## Contexto

Padrões hexagonal inconsistentes entre módulos. R2 exige padrão único obrigatório.

## Decisão — Padrão obrigatório (todos os contextos)

### Estrutura de pastas

```
modules/{context}/
  domain/
    entities/
    value_objects/
    events/
    exceptions/
  application/
    commands/
    queries/
    ports/          ← Protocol interfaces
    services/
  infrastructure/
    repositories/   ← SQLAlchemy adapters
    adapters/       ← external integrations
shared/acl/
  {context}_port.py ← Legacy ACL adapters ONLY
```

### Camadas e dependências

```
domain        → (nothing external)
application   → domain, ports (Protocol)
infrastructure→ application ports, domain, ORM, ACL
routers       → application only
ACL           → legado services/models ONLY
```

### Padrão Repository

| Elemento | Regra |
|----------|-------|
| Interface | `Protocol` in `application/ports/{entity}_repository.py` |
| Methods | `get_by_id`, `save`, `delete` — domain types in/out |
| Adapter | `{Entity}SqlAlchemyRepository` in `infrastructure/repositories/` |
| Tenant | Every query filters `company_id` |
| Mapping | ORM model ↔ domain entity in adapter private methods |

### Padrão ACL

| Elemento | Regra |
|----------|-------|
| Location | `shared/acl/{context}_port.py` |
| Naming | `Legacy{Context}Adapter` implements `{Context}Port` |
| Responsibility | Translate legado ↔ core DTOs only |
| Prohibited | Business rules in ACL |

### Aplicação por contexto

| Context | Repository Port | ACL Port | Fase |
|---------|-----------------|----------|------|
| **Booking** | `CoreBookingRepository` | `LegacyBookingPort` | F1, F0.5 |
| **Catalog** | `CatalogRepository` | `LegacyCatalogPort` | F3b |
| **Customer** | `CustomerRepository` | `LegacyCustomerPort` | F3b |
| **Payments** | `PaymentRepository` (read R2) | `LegacyPaymentPort` | F2 query only |
| **Scheduling** | N/A (engine) | `LegacySchedulingPort` → `ResourcePort` | F1, F3 |
| **Resource** | `CoreResourceRepository` | `LegacyResourceMappingPort` | F3 |
| **Plugins** | `PluginRegistryRepository` | N/A | F4 |

### Query vs Command

| Type | Port suffix | Layer |
|------|-------------|-------|
| Write | `Repository` | Command handlers |
| Read cross-context | `QueryPort` | Application services |
| Legado bridge | `Legacy*Port` in ACL | Adapter only |

### Unit of Work

- Single `Session` per HTTP request (existing FastAPI dependency)
- Repository adapters receive session via constructor
- TX boundaries per ADR-025

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Active Record in domain | ❌ Violates hexagonal |
| B | Protocol ports + adapters | ✅ Escolhida |
| C | Generic repository | ❌ Leaky abstraction |

## Consequências

- FF-HEX-005 enforces folder structure
- F0.5 wires ACL before domain pure
- Payments full repository deferred R3

## Referências

- `docs/CONSTITUTION.md` Artigo II
- ADR-005 Core Framework
