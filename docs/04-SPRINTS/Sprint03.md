# Sprint 3 — MySQL Docker + Frontend v1 + Sunset Legado

**Objetivo:** Infra MySQL via Docker, frontend consumindo scheduling v1, depreciação formal das rotas legado.

## Entregas

| Item | Status |
|------|--------|
| `docker-compose.mysql.yml` (MySQL 8 + API) | ✅ |
| `pymysql` + Alembic no startup MySQL | ✅ |
| `scripts/docker-entrypoint.sh` (wait + migrate) | ✅ |
| Middleware `LegacySunsetMiddleware` (RFC 8594) | ✅ |
| Frontend `coreflowService.ts` | ✅ |
| `agendamentoService` → v1 com fallback legado | ✅ |
| `EXPO_PUBLIC_USE_COREFLOW_V1` (default true) | ✅ |
| Testes sunset + docs | ✅ |
| Redis / Kafka | 🔜 Sprint 4 |

## Docker MySQL

```bash
make docker-mysql-up    # API :8000 + MySQL :3306
make docker-mysql-down
```

Credenciais padrão:
- Database: `coreflow`
- User/Password: `coreflow` / `coreflow`

Dev local continua com SQLite: `make migrate` / `make run`.

## Sunset headers (legado)

Rotas afetadas recebem:

```
Sunset: Sat, 01 Jul 2027 00:00:00 GMT
Deprecation: true
Link: </v1/catalogs>; rel="successor-version"
```

| Legado | Sucessor v1 |
|--------|-------------|
| `/trancas` | `/v1/catalogs` |
| `/agenda/disponibilidade` | `/v1/scheduling/availability` |
| `/agenda/agendamentos` | `/v1/bookings` |
| `/reservations` | `/v1/bookings` |

Desabilitar: `LEGACY_SUNSET_ENABLED=false`

## Frontend CoreFlow v1

Fluxo de agendamento (`agendar/[id].tsx`):

```
agendamentoService.consultarDisponibilidade
  → coreflowService.resolveLegacyIds(trancaId, serviceImageId)
  → GET /v1/scheduling/availability
  → fallback /agenda/disponibilidade se v1 falhar
```

Variável: `EXPO_PUBLIC_USE_COREFLOW_V1=false` força legado.

## Validar

```bash
make test
curl -I http://localhost:8000/trancas   # ver Sunset headers
cd frontend && npm run typecheck
```

## Próximo: Sprint 4

- Redis cache + filas
- POST /v1/bookings no fluxo cliente
- CI com job MySQL
