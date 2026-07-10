# Sprint 18 — EAS Submit + Avro Evolution + CloudFront Behaviors

## Entregas

| Item | Status |
|------|--------|
| `EasSubmitService` — submit App Store / Play por plugin | ✅ |
| `mobile.submit:` nos manifests | ✅ |
| `frontend/eas.submit.json` + `scripts/eas-submit.sh` | ✅ |
| GitHub Actions job `eas-submit` | ✅ |
| `AvroEvolutionService` — compatibilidade BACKWARD | ✅ |
| `booking.approved.v2.avsc` (campo `approved_by`) | ✅ |
| Confluent `check_compatibility` API | ✅ |
| `CloudFrontBehaviorsService` — cache por tenant | ✅ |
| Export `infra/cdn/cloudfront-behaviors.json` | ✅ |
| Versão `1.8.0-sprint18` | ✅ |

## EAS Submit por plugin

```yaml
mobile:
  submit:
    ios:
      asc_app_id: "1000000002"
      apple_id: "sports@coreflow.app"
    android:
      track: internal
      service_account_key: "./credentials/sports-play-service-account.json"
```

```bash
make eas-submit-generate
GET /v1/mobile/eas/submit/profiles
./scripts/eas-submit.sh sports ios
```

GitHub Actions: job `eas-submit` (profile=production + workflow_dispatch).

## Avro Schema Evolution

```bash
GET /v1/events/schemas/avro/evolution
GET /v1/events/schemas/avro/booking.approved/versions
POST /v1/events/schemas/avro/check-compatibility?old_schema_id=booking.approved.v1&new_schema_id=booking.approved.v2
POST /v1/events/schemas/avro/register-evolved?event_type=booking.approved
```

Regras BACKWARD: campos novos com `default`; remoção de campos proibida.

## CloudFront behaviors por tenant

```bash
GET /v1/mobile/cdn/cloudfront-behaviors
GET /v1/mobile/cdn/cloudfront-behaviors?plugin_id=sports
make export-cloudfront-behaviors
```

Cada plugin: `/{plugin_id}/.well-known/*` com TTL e compressão.

## Concluído em CF-19

Ver [`Sprint19.md`](./Sprint19.md).
