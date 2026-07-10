# Sprint 1 — Core Platform + Metamodelo

**Objetivo:** Entidades genéricas Catalog/Offering/Booking ao lado do legado (Strangler Fig).

## Entregas

| Item | Status |
|------|--------|
| Tabelas `core_catalogs`, `core_offerings`, `core_bookings` | ✅ |
| LegacySyncService (Tranca → Catalog, etc.) | ✅ |
| API GET `/v1/catalogs` | ✅ |
| API GET `/v1/catalogs/{id}/offerings` | ✅ |
| CQRS CreateBookingCommand + Handler | ✅ |
| API POST/GET `/v1/bookings` | ✅ |
| Sync no startup (bootstrap) | ✅ |
| Testes v1 | ✅ |
| Alembic + MySQL | 🔜 Sprint 2 |
| Entidades Worker, Resource, Location | 🔜 Sprint 2 |

## Mapeamento metamodelo

| CoreFlow | Tabela | Legado |
|----------|--------|--------|
| Catalog | core_catalogs | trancas |
| Offering | core_offerings | service_images |
| Booking | core_bookings | agendamentos |

## Fluxo CQRS CreateBooking

```
POST /v1/bookings
    → CreateBookingCommand
    → resolve legacy IDs (catalog/offering)
    → ReservationService.criar_de_schema (regras existentes)
    → sync core_bookings
    → reservation.created event
```

## APIs paralelas (transição)

| Legado | CoreFlow v1 |
|--------|-------------|
| GET /trancas | GET /v1/catalogs |
| GET /trancas/{id}/modelos | GET /v1/catalogs/{id}/offerings |
| POST /reservations | POST /v1/bookings |

## Validar

```bash
make migrate
make test
curl http://localhost:8000/v1/catalogs
curl http://localhost:8000/v1/catalogs/1/offerings
```

## Próximo: Sprint 2

- Scheduling engine genérico (Resource + Worker)
- Alembic baseline
- Deprecar endpoints legado (headers Sunset)
