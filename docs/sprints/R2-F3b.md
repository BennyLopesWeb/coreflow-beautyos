# Release 2 — Sprint R2-F3b

**Documento operacional único desta sprint** — Catalog + Customer repositories (ADR-030).

---

## 1. Identificação da Sprint

| Campo | Valor |
|-------|-------|
| **Sprint** | R2-F3b |
| **Versão** | `1.21.1-r2-f3b` |
| **Status** | ✅ Implemented (tech) — `1.21.1-r2-f3b` |
| **Release** | R2 — Core Domain Consolidation |
| **Fase anterior** | R2-F3 ✅ Implemented (`1.21.0-r2-f3`) |
| **Próxima fase** | R2-F4 — Plugin Engine + BeautyAgent |
| **Owner** | Platform Team |
| **Objetivo estratégico** | Completar ports/repos Catalog + Customer (FF-HEX-006), ACL legado, e corrigir TD-R2-F2-002 (duração no load do aggregate). |

**Gate anterior:** [R2-F3-Gate.md](../reviews/R2-F3-Gate.md) ✅ IMPLEMENTED

---

## 2. Objetivo

Com ADR-030 e ADR-009:

- `CatalogRepository` + adapter SQLAlchemy em `modules/catalog/`
- `CustomerRepository` + adapter SQLAlchemy em `modules/customer/`
- `LegacyCatalogPort` / `LegacyCustomerPort` em `shared/acl/`
- Query ports usados pelo booking create (CustomerQueryPort) e catalog read
- Fix **TD-R2-F2-002**: `_to_domain` carrega `duration_minutes` do offering
- `APP_VERSION=1.21.1-r2-f3b`

**Sem nova feature flag** — rollback = git revert.

---

## 3. Escopo IN

| # | Entrega |
|---|---------|
| 1 | `CatalogRepository` Protocol + `SqlAlchemyCatalogRepository` |
| 2 | Mover `SqlAlchemyCatalogQueryAdapter` para `modules/catalog/` (re-export no booking) |
| 3 | `shared/acl/catalog_port.py` — LegacyCatalogPort |
| 4 | `CustomerRepository` Protocol + `SqlAlchemyCustomerRepository` |
| 5 | `CustomerQueryPort` + adapter (valida `clientes.id` — FK booking) |
| 6 | `shared/acl/customer_port.py` — LegacyCustomerPort |
| 7 | Wiring create_booking → CustomerQueryPort |
| 8 | Fix TD-R2-F2-002 em `core_booking_repository._to_domain` |
| 9 | Testes FF-HEX-006 + duration load |
| 10 | Emenda tiering: catalog/customer → **CORE-SUPPORT** (hexagonal lite) |

---

## 4. Escopo OUT

| Item | Fase |
|------|------|
| Plugin Engine / P10 | R2-F4 |
| Flatten catalog Wave 2 | Cancelado — reclassificado CORE-SUPPORT |
| Migrar FK booking `customer_id` → `core_customers` | R3+ |
| Aggregate/events Catalog/Customer | OUT |
| Enforcement / OTEL | R2-F5 / F6 |

---

## 5. Decisão de tiering (obrigatória)

**ADR-030 + FF-HEX-006 prevalecem** sobre o flatten CRUD de `catalog`/`customer`.

Emenda [ModuleTieringPolicy](../architecture/ModuleTieringPolicy.md): ambos passam a **CORE-SUPPORT** (hexagonal lite — ports/repos/ACL, sem aggregates/events). Freeze flat de `customer` é **excepcionado** para ports F3b.

---

## 6. DoD

| # | Critério |
|---|----------|
| 1 | Ports `CatalogRepository` e `CustomerRepository` existem |
| 2 | ACL LegacyCatalog/Customer Port |
| 3 | TD-R2-F2-002 fechado (duration ≠ 30 no load) |
| 4 | Create valida customer via QueryPort |
| 5 | pytest suite green |
| 6 | `APP_VERSION=1.21.1-r2-f3b` |
| 7 | Decision Log + Gate atualizados |

---

## 7. Critério de GO para R2-F4

| # | Gate |
|---|------|
| G1 | DoD F3b completo |
| G2 | Zero regressão booking lifecycle |
| G3 | FF-HEX-006 WARN satisfeito (ports presentes) |
| G4 | Sprint doc R2-F4 / DoR F4 |
