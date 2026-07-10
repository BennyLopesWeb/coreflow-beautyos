# 11 — Mobile Strategy

## Visão

Estratégia mobile multi-plugin: Expo (BeautyOS piloto) → SDK TypeScript → Flutter (futuro).

## Estado atual

| App / Pacote | Stack | Status |
|--------------|-------|--------|
| BeautyOS | Expo + React Native | ✅ piloto |
| EAS Build | `eas.json` dev/preview/production | ✅ CF-15 |
| Deep links | scheme + universal links + CDN | ✅ CF-15 |
| Push | expo-notifications + Expo Push API | ✅ CF-14/15 |
| Kafka schemas | JSON Schema Registry | ✅ CF-15 |

## CDN `.well-known` (CF-15)

```bash
make export-well-known
make docker-cdn-up    # nginx :8080
GET /v1/mobile/cdn/manifest
```

## EAS Build (CF-15)

```bash
cd frontend
npm run eas:build:preview
npm run eas:build:production
```

Credenciais push via `eas credentials` + backend `EXPO_PUSH_LIVE=true`.

## Schema Registry (CF-15)

Eventos Kafka envelopados com `schema_id` — ver `GET /v1/events/schemas`.

## Próximos passos (CF-16+)

- Confluent Schema Registry (Avro)
- CDN multi-tenant por plugin
- CI/CD EAS automatizado
