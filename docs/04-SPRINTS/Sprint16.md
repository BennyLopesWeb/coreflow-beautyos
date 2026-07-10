# Sprint 16 — Confluent SR + CDN Multi-Plugin + EAS CI/CD

## Entregas

| Item | Status |
|------|--------|
| `ConfluentSchemaRegistryClient` (HTTP REST) | ✅ |
| `KAFKA_SCHEMA_REGISTRY_MODE=file\|confluent` | ✅ |
| Avro schemas + `AvroEventCodec` (Confluent wire) | ✅ |
| `PluginCdnService` — CDN por plugin | ✅ |
| `mobile:` nos manifests beauty/sports/clinic | ✅ |
| `POST /v1/mobile/well-known/export-all` | ✅ |
| `GET /v1/mobile/cdn/plugins` | ✅ |
| `GET /v1/events/schema-registry/health` | ✅ |
| `docker-compose.schema-registry.yml` | ✅ |
| GitHub Actions `mobile-eas.yml` | ✅ |
| `scripts/eas-ci.sh` | ✅ |
| Versão `1.6.0-sprint16` | ✅ |

## Confluent Schema Registry

```bash
make docker-schema-registry-up
KAFKA_SCHEMA_REGISTRY_MODE=confluent
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081
KAFKA_SCHEMA_ENCODING=json   # ou avro

GET /v1/events/schema-registry/health
```

Envelope Kafka com `confluent_schema_id` + `confluent_subject`.

Avro: `backend/schemas/events/avro/*.avsc` + fastavro wire format.

## CDN multi-tenant por plugin

```bash
make export-well-known-all
GET /v1/mobile/cdn/manifest
GET /v1/mobile/cdn/manifest?plugin_id=sports
```

Estrutura exportada:

```
backend/cdn/.well-known/           # global agregado
backend/cdn/beauty/.well-known/
backend/cdn/sports/.well-known/
backend/cdn/clinic/.well-known/
```

Manifests declaram `mobile.cdn_host` por vertical.

## EAS CI/CD

```bash
export EXPO_TOKEN=xxx
./scripts/eas-ci.sh preview all
./scripts/eas-ci.sh production android
```

GitHub Actions: `.github/workflows/mobile-eas.yml`
- Trigger: `workflow_dispatch` ou tag `mobile/v*`
- Secrets: `EXPO_TOKEN`
- Artifact: `well-known-cdn` exportado

## Concluído em CF-17

Ver [`Sprint17.md`](./Sprint17.md).
