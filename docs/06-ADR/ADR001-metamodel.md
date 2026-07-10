# ADR-001 — Metamodelo Genérico CoreFlow

| | |
|---|---|
| **Status** | Aceito |
| **Data** | 2026-07-09 |
| **Contexto** | Sprint 0 CoreFlow |

## Contexto

BeautyOS codificava conceitos verticais (`Tranca`, `ServiceImage`, `Agendamento`).  
Para suportar SportsOS, ClinicOS etc. sem reescrever o core, precisamos de um **metamodelo genérico**.

## Decisão

O núcleo CoreFlow opera sobre conceitos genéricos:

| Conceito | Descrição |
|----------|-----------|
| **Company** | Tenant SaaS |
| **User / Worker** | Quem executa serviços |
| **Customer** | Cliente final |
| **Location** | Unidade física |
| **Resource** | O que é reservado (cadeira, quadra, sala) |
| **Catalog** | Agrupador de serviços |
| **Service** | Tipo de serviço |
| **Offering** | Variante comercial (preço, duração) |
| **Booking** | Reserva |
| **ScheduleBlock** | Bloco na agenda |
| **Waitlist / Queue** | Filas |

Plugins **especializam terminologia** via `manifest.yaml`, não duplicam entidades core.

## Mapeamento Beauty (legado → metamodelo)

| Metamodelo | Entidade legado atual |
|------------|----------------------|
| Catalog | `Tranca` |
| Offering | `ServiceImage` |
| Booking | `Agendamento` |
| Customer | `Cliente` |

## Consequências

### Positivas
- Novos verticais = novo manifest + metadata JSON  
- Scheduling engine reutilizável  
- Build Once. Configure Everywhere.  

### Negativas
- Migração gradual (Strangler Fig) necessária  
- Dupla nomenclatura temporária (`/trancas` + `/v1/services` futuro)  

## Implementação Sprint 0

- `app/core/metamodel/concepts.py` — enum `CoreConcept`  
- `backend/plugins/beauty/manifest.yaml` — terminologia + mappings  
- `Company.plugin_id` — plugin ativo por tenant  

## Referências

- `COREFLOW_ANALYSIS.md`  
- `docs/03-PLUGINS/Beauty.md`  
