# Sprint 13 — Expo Push API + Universal Links + Outbox RabbitMQ

## Entregas

| Item | Status |
|------|--------|
| `ExpoPushClient` — API real + fallback mock | ✅ |
| Universal links (`https://app.coreflow.app/{tenant}/...`) | ✅ |
| `OUTBOX_DISPATCH_MODE=sync\|deferred\|rabbitmq` | ✅ |
| `RabbitMQEventAdapter` + fila `coreflow.events` | ✅ |
| Worker CLI `app.workers.outbox_worker` | ✅ |
| API admin `GET /v1/outbox/status`, `POST /v1/outbox/replay` | ✅ |
| Docker overlay `docker-compose.rabbitmq.yml` | ✅ |
| Frontend App Links (iOS/Android) | ✅ |
| Versão `1.3.0-sprint13` | ✅ |

## Expo Push API

```bash
EXPO_PUSH_LIVE=true
EXPO_PUSH_ACCESS_TOKEN=your-expo-access-token
PUSH_NOTIFICATIONS_ENABLED=true
```

Tokens mock (`ExponentPushToken[dev-...]`) continuam em modo local.

## Universal Links

```
https://app.coreflow.app/salao-demo/bookings/42
trancapro://salao-demo/bookings/42
```

Manifest: `sdk.deep_links.universal_host`

Frontend: `associatedDomains` (iOS) + `intentFilters` (Android) em `app.json`

## Outbox Worker

Modos:

| Modo | Comportamento |
|------|---------------|
| `sync` | Publica imediatamente no event bus (default) |
| `deferred` | Persiste pending; worker poll processa |
| `rabbitmq` | Enfileira AMQP; worker consome e publica handlers |

```bash
# Poll manual (dev)
make outbox-worker

# Worker contínuo
cd backend && python -m app.workers.outbox_worker --mode poll --interval 5

# RabbitMQ stack
make docker-rabbitmq-up
cd backend && python -m app.workers.outbox_worker --mode rabbitmq
```

Admin replay:

```bash
GET  /v1/outbox/status
POST /v1/outbox/replay
```

## Próximo: CF-14

- Universal links `.well-known` hosting
- Expo Notifications nativo no app
- Kafka adapter (event bus produção)

## Concluído em CF-14

Ver [`Sprint14.md`](./Sprint14.md).
