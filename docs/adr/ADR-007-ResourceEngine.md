# ADR-007 — Resource Engine

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2026-07-09 |

## Contexto

Toda reserva na CoreFlow opera sobre **Resources** abstratos. Piloto beauty mapeia Resource → Cadeira via manifest.

## Problema

Resource Engine parcial; regras ainda conhecem legado (`LegacySchedulingAdapter`).

## Decisão

### Conceitos universais (Resource Engine)

| Conceito | Definição | Entidade |
|----------|-----------|----------|
| **Location** | Unidade física onde resources existem | `CoreLocation` |
| **Resource** | Entidade reservável (cadeira, quadra, sala, equipamento) | `CoreResource` |
| **Worker** | Agente que executa serviço (pode ser alocado a resource) | `CoreWorker` |
| **Asset** | Ativo controlado (estoque, equipamento permanente) | `CoreAsset` |
| **Capacity** | Quantidade simultânea suportada por resource | `CoreResource.capacity` |
| **Availability** | Slots livres calculados | `SchedulingEngine.check_availability()` |

### Regras imutáveis

1. **Nenhuma regra** no engine referencia tipo semântico (cadeira vs quadra) — apenas `resource_id`, `capacity`, blocks
2. Tipo exibido = `plugin.terminology.resource` + metadata opcional no manifest
3. Conflitos via `ResourceConflictService` — genérico
4. Hierarquia resource (parent/child) — 🔜 Release 2–3
5. Integração legado **somente** via ACL (`LegacySchedulingAdapter` → migrar para port)

### Engine components (path)

- `scheduling/engine/scheduling_engine.py`
- `scheduling/engine/resource_conflict.py`
- `scheduling/application/availability_service.py`

## Consequências

- Remoção do adapter legado é prerequisite para Scheduling v2
- Multi-resource booking requer ADR futuro

## Benefícios

- SportsOS/ClinicOS reutilizam mesmo engine

## Trade-offs

- Adapter legado temporário aumenta complexidade

## Referências

- `docs/resource-engine/README.md`
- `docs/CoreMetaModel.md`
- ADR-001 metamodelo
