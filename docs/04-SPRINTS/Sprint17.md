# Sprint 17 — EAS White-Label + Avro Completo + CDN S3/CloudFront

## Entregas

| Item | Status |
|------|--------|
| `EasWhitelabelService` — perfis EAS por plugin | ✅ |
| `mobile:` com ios_bundle_id, eas_project_id, expo_slug | ✅ |
| `frontend/eas.plugins.json` gerado via API/Makefile | ✅ |
| Avro `.avsc` para todos os 5 eventos | ✅ |
| `GET /v1/events/schemas/avro` + `/coverage` | ✅ |
| `POST /v1/events/schemas/avro/register-all` | ✅ |
| `CdnS3SyncService` — S3 + CloudFront invalidation | ✅ |
| `POST /v1/mobile/cdn/sync-s3` | ✅ |
| GitHub Actions `cdn-sync.yml` | ✅ |
| `scripts/cdn-sync-s3.sh` + `eas-ci.sh` plugin-aware | ✅ |
| Versão `1.7.0-sprint17` | ✅ |

## EAS White-Label por plugin

Cada manifest declara bundle IDs e projeto EAS próprios:

```yaml
mobile:
  ios_bundle_id: com.coreflow.sports
  android_package: com.coreflow.sports
  app_name: SportsOS
  expo_slug: sportsos
  eas_project_id: coreflow-sports-dev
```

```bash
make eas-generate
GET /v1/mobile/eas/profiles?profile=preview
GET /v1/mobile/eas/profiles/sports?profile=production
./scripts/eas-ci.sh preview all sports
```

Perfis EAS gerados: `beauty-preview`, `sports-production`, etc.

## Avro em todos os eventos

Schemas em `backend/schemas/events/avro/`:

- `booking.approved.v1.avsc`
- `booking.created.v1.avsc`
- `booking.rejected.v1.avsc`
- `reservation.created.v1.avsc`
- `payment.deposit.confirmed.v1.avsc`

```bash
KAFKA_SCHEMA_ENCODING=avro
KAFKA_SCHEMA_REGISTRY_MODE=confluent
GET /v1/events/schemas/avro/coverage   # 100% complete
POST /v1/events/schemas/avro/register-all
```

## CDN S3/CloudFront sync

```bash
make cdn-sync-s3              # dry-run (default)
make cdn-sync-s3-live         # upload real (requer credenciais)

CDN_S3_BUCKET=coreflow-cdn
CDN_S3_PREFIX=cdn
CDN_CLOUDFRONT_DISTRIBUTION_ID=E1234567890
CDN_S3_ENABLED=true
CDN_S3_DRY_RUN=false
```

GitHub Actions: `.github/workflows/cdn-sync.yml`
- Trigger: `workflow_dispatch` ou tag `cdn/v*`
- Secrets: `CDN_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `CDN_CLOUDFRONT_DISTRIBUTION_ID`

## Concluído em CF-18

Ver [`Sprint18.md`](./Sprint18.md).
