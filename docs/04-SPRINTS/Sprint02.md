# Sprint 2 — Scheduling Engine + Alembic

**Objetivo:** Formalizar Location, Worker, Resource e ScheduleBlock; expor scheduling engine genérico via API v1; baseline Alembic para MySQL.

## Entregas

| Item | Status |
|------|--------|
| Tabelas `core_locations`, `core_workers`, `core_resources`, `core_schedule_blocks` | ✅ |
| `SchedulingLegacySyncService` (defaults + espelho `schedules`) | ✅ |
| API GET `/v1/locations`, `/v1/workers`, `/v1/resources` | ✅ |
| API GET `/v1/scheduling/availability` | ✅ |
| `SchedulingAvailabilityService` (delega legado via catalog/offering) | ✅ |
| Alembic `env.py` + revisions `cf001` / `cf002` | ✅ |
| `make alembic-upgrade` | ✅ |
| Testes scheduling v1 | ✅ |
| MySQL produção | 🔜 Sprint 3 |
| Sunset headers APIs legado | 🔜 Sprint 3 |

## Mapeamento metamodelo

| CoreFlow | Tabela | Legado (beauty) |
|----------|--------|-----------------|
| Location | core_locations | implicit_single_location (Company) |
| Worker | core_workers | UserCompany (owner/professional) |
| Resource | core_resources | implicit_single_chair (capacidade 1) |
| ScheduleBlock | core_schedule_blocks | schedules |

## Scheduling engine

```
GET /v1/scheduling/availability
    → resolve catalog/offering → tranca/service_image (Strangler)
    → DisponibilidadeService.calcular_horarios_disponiveis
    → AvailabilitySlotResponse (starts_at, available, resource_id, worker_id)
```

No plugin beauty (1 cadeira / 1 profissional), `resource_id` e `worker_id` retornam defaults do tenant.

## Alembic

| Revision | Conteúdo |
|----------|----------|
| `cf001_metamodel` | core_catalogs, core_offerings, core_bookings |
| `cf002_scheduling` | core_locations, core_workers, core_resources, core_schedule_blocks |

```bash
make migrate          # dev SQLite: create_all + sync
make alembic-upgrade  # produção / MySQL: alembic upgrade head
```

`DATABASE_URL` vem de `.env` ou `app.core.config.settings`.

## Validar

```bash
make test
curl "http://localhost:8000/v1/locations"
curl "http://localhost:8000/v1/resources"
curl "http://localhost:8000/v1/scheduling/availability?date=2026-07-15T00:00:00&catalog_id=1&offering_id=1"
```

## Próximo: Sprint 3

- Docker Compose com MySQL + Redis
- Migração schema legado completo para Alembic
- Frontend consumindo `/v1/scheduling/availability`
- Headers `Sunset` em rotas legado
