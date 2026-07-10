# Resource Engine

Motor genérico de recursos reserváveis — **nenhuma regra conhece o tipo do Resource**.

**Documentação estratégica completa:** [`../ResourceEngine.md`](../ResourceEngine.md)

## Estado atual

| Componente | Arquivo | Status |
|------------|---------|--------|
| CoreResource ORM | `modules/scheduling/domain/models.py` | ✅ |
| ResourceConflictService | `scheduling/engine/resource_conflict.py` | ✅ |
| Capacity | field `capacity` em CoreResource | ✅ |
| API | `/v1/resources` | ✅ |

## Gap vs destino

- Hierarquia de resources (parent/child)
- Tipos plugáveis via plugin manifest
- Resource pools e alocação multi-resource
- Pricing rules por resource

SAB: `docs/07-META-MODEL/`, `docs/COREFLOW_GAP_ANALYSIS.md` §3
