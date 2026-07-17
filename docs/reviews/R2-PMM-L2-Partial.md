# PMM L2 Partial Assessment — R2 Exit (`2.0.0-beta.1`)

**Modelo:** [PlatformMaturityModel.md](../PlatformMaturityModel.md)  
**Data:** 2026-07-16  
**Meta R2:** ≥65% critérios L2 parciais

## Scorecard

| Critério L2 | Peso | Status | Nota |
|-------------|------|--------|------|
| Booking domain puro (ports/ACL) | 15 | ✅ | F1–F2b |
| Resource Engine v1 | 10 | ✅ | F3 |
| Hexagonal Catalog/Customer | 10 | ✅ | F3b |
| Plugin Engine + BeautyAgent fora de modules/ai | 10 | ✅ | F4 |
| Paridade 12/12 | 15 | ✅ | P01–P12 testes |
| Fitness CI ERROR | 10 | ✅ | F5 |
| OTEL core booking path | 5 | ✅ | F5 |
| Reconciliation / drift metric | 5 | ✅ | F5 |
| Enforcement narrow staging | 10 | ✅ | F6 |
| Coupling ≤3 | 5 | ✅ | F5 |
| Tests ≥300 | 5 | ✅ | 340+ |

**Pontuação:** 100 / 100 critérios listados · **≥65% ✅**

## Lacunas conscientes (R3+)

- Production `CORE_ENFORCEMENT_MODE=block`
- Block payments/fila
- Remoção física de routers legado
- PMM L2 full (Integration Hub, BI, Marketplace)
