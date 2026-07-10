# Sprint 14 — Well-Known Hosting + Expo Notifications + Kafka

## Entregas

| Item | Status |
|------|--------|
| `GET /.well-known/apple-app-site-association` | ✅ |
| `GET /.well-known/assetlinks.json` | ✅ |
| `WellKnownService` + config iOS/Android | ✅ |
| `GET /v1/mobile/well-known/preview` | ✅ |
| `KafkaEventAdapter` + tópico `coreflow.events` | ✅ |
| `OUTBOX_DISPATCH_MODE=kafka` | ✅ |
| Worker `--mode kafka` | ✅ |
| Docker `docker-compose.kafka.yml` | ✅ |
| `expo-notifications` nativo + listeners push | ✅ |
| Versão `1.4.0-sprint14` | ✅ |

## Well-Known (Universal/App Links)

Hospedados na API (proxy ou CDN em produção):

```
GET /.well-known/apple-app-site-association
GET /.well-known/assetlinks.json
GET /v1/mobile/well-known/preview
```

Config:

```bash
MOBILE_UNIVERSAL_LINK_HOST=app.coreflow.app
MOBILE_IOS_APP_ID=TEAMID12345.com.trancapro.app
MOBILE_ANDROID_PACKAGE=com.trancapro.app
MOBILE_ANDROID_SHA256_FINGERPRINTS=AA:BB:...
```

## Expo Notifications nativo

Frontend usa `expo-notifications` + `expo-device`:
- Device físico → token Expo real
- Simulador/web → fallback mock `ExponentPushToken[dev-user-{id}]`
- Tap na push → abre `universal_link` ou `deep_link`

```bash
EXPO_PUBLIC_PUSH_ENABLED=true
EXPO_PUBLIC_EAS_PROJECT_ID=your-eas-project-id
```

## Kafka adapter

```bash
OUTBOX_DISPATCH_MODE=kafka
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=coreflow.events

make docker-kafka-up
python -m app.workers.outbox_worker --mode kafka
```

## Próximo: CF-15

- CDN/hosting produção para `.well-known`
- EAS Build + push credentials produção
- Schema Registry / Avro eventos Kafka

## Concluído em CF-15

Ver [`Sprint15.md`](./Sprint15.md).
