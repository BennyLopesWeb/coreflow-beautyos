# Sprint 15 — CDN Well-Known + EAS Build + Schema Registry

## Entregas

| Item | Status |
|------|--------|
| CDN cache headers em `.well-known` | ✅ |
| `WellKnownExportService` → `backend/cdn/` | ✅ |
| `GET /v1/mobile/cdn/manifest` | ✅ |
| `POST /v1/mobile/well-known/export` (admin) | ✅ |
| Nginx + `docker-compose.cdn.yml` | ✅ |
| `frontend/eas.json` (dev/preview/production) | ✅ |
| JSON Schema Registry file-based | ✅ |
| `GET /v1/events/schemas` | ✅ |
| Kafka envelope `schema_id` + validação | ✅ |
| Versão `1.5.0-sprint15` | ✅ |

## CDN produção `.well-known`

```bash
make export-well-known          # grava backend/cdn/.well-known/
make docker-cdn-up              # nginx :8080 servindo CDN estático
GET  /v1/mobile/cdn/manifest    # URLs + cache headers
POST /v1/mobile/well-known/export  # admin
```

Config:

```bash
MOBILE_CDN_ENABLED=true
MOBILE_CDN_BASE_URL=https://app.coreflow.app
MOBILE_WELL_KNOWN_CACHE_SECONDS=86400
```

Deploy: sync `backend/cdn/.well-known/` → S3/CloudFront ou use `infra/nginx/well-known.conf`.

## EAS Build + Push produção

```bash
cd frontend
npm run eas:build:preview      # APK/internal
npm run eas:build:production   # App Store / Play Store
```

`eas.json` profiles com `EXPO_PUBLIC_PUSH_ENABLED=true`.

Credenciais push:
- iOS: APNs key via EAS (`eas credentials`)
- Android: FCM via EAS
- Backend: `EXPO_PUSH_LIVE=true` + `EXPO_PUSH_ACCESS_TOKEN`

## Schema Registry Kafka

Schemas em `backend/schemas/events/*.json`:

```bash
GET /v1/events/schemas
GET /v1/events/schemas/booking.approved.v1

KAFKA_SCHEMA_REGISTRY_ENABLED=true
KAFKA_SCHEMA_VALIDATE=true
KAFKA_SCHEMA_ENCODING=json
```

Envelope Kafka:

```json
{
  "schema_id": "booking.approved.v1",
  "schema_version": 1,
  "encoding": "json",
  "outbox_id": 42,
  "event": { ... }
}
```

## Concluído em CF-16

Ver [`Sprint16.md`](./Sprint16.md).
