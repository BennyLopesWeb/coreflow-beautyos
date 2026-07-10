# Sprint 0 — CoreFlow Platform

**Objetivo:** Arquitetura only. Sem features novas de negócio.

## Entregas

| Item | Status |
|------|--------|
| Monorepo + docs/ SAB | ✅ |
| Plugin Loader v0 | ✅ |
| Manifest beauty | ✅ |
| Metamodelo (CoreConcept) | ✅ |
| API GET /v1/plugins | ✅ |
| Company.plugin_id | ✅ |
| Modular Monolith (identity) | ✅ |
| Event Bus in-memory | ✅ |
| JWT + RBAC + multi-tenant | ✅ |
| Docker + Makefile | ✅ |
| GitHub Actions CI | ✅ |
| Testes (38+) | ✅ |
| Alembic + MySQL | 🔜 Sprint 1 |
| CQRS | 🔜 Sprint 1 |
| OpenTelemetry | 🔜 Sprint 1 |
| React + Flutter apps | 🔜 Sprint 8+ |
| Plugin sports/clinic | 🔜 Sprint 8+ |

## Como validar

```bash
make install
make migrate
make test
make run
# GET http://localhost:8000/v1/plugins
# GET http://localhost:8000/v1/plugins/config/by-company/salao-demo
```

## Próximo: Sprint 1 — Core Platform

- Entidades genéricas Catalog/Service/Offering/Booking (ao lado do legado)  
- CQRS commands/queries para Booking  
- Alembic + MySQL  

Ver `docs/04-SPRINTS/Sprint01.md` (a criar).
