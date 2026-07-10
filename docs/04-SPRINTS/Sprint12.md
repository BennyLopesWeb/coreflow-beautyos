# Sprint 12 — Deep Links + Push via Outbox + Production Block

## Entregas

| Item | Status |
|------|--------|
| `core_device_tokens` + Alembic `cf009_device_tokens` | ✅ |
| API POST `/v1/devices/register` | ✅ |
| `PushNotificationService` — push mock + deep link no payload | ✅ |
| Handlers push no event bus (booking.*, payment.deposit.confirmed) | ✅ |
| `sdk.deep_links` nos manifests beauty/sports/clinic | ✅ |
| `GET /v1/plugins/config` expõe `deep_links` | ✅ |
| Frontend `deepLinkService` + listener em `_layout.tsx` | ✅ |
| Registro push mock após login | ✅ |
| `APP_ENV=production` → enforcement **block** | ✅ |
| Versão `1.2.0-sprint12` | ✅ |

## Deep Links

Formato: `{scheme}://{tenant_slug}{path}`

```
trancapro://salao-demo/bookings/42
trancapro://salao-demo/admin/reservas/42
trancapro://salao-demo/agendar/3
```

Declarados em `manifest.yaml` → `sdk.deep_links.routes`.

Frontend: `frontend/src/services/deepLinkService.ts`

## Push via Outbox

Fluxo:

1. Evento outbox (`booking.approved`, etc.)
2. `PushNotificationService.handle_domain_event()`
3. Monta deep link por plugin/tenant
4. Envia push mock → `notification_logs` (tipo `push`)

Registro de device:

```bash
POST /v1/devices/register
{"expo_push_token": "ExponentPushToken[...]", "platform": "android"}
```

Config:

```bash
PUSH_NOTIFICATIONS_ENABLED=true
MOBILE_DEEP_LINK_SCHEME=trancapro
```

## Production Enforcement (fase final)

```bash
APP_ENV=production make run          # block legado writes por default
CORE_ENFORCEMENT_MODE=warn ...       # rollback gradual se necessário
```

Prioridade: `CORE_ENFORCEMENT_ENABLED` → modo explícito → staging block → **production block** → off

## Próximo: CF-13

- Expo Push API real (EXPO_PUSH_ACCESS_TOKEN)
- Universal links (iOS/Android)
- Worker assíncrono outbox → RabbitMQ

## Concluído em CF-13

Ver [`Sprint13.md`](./Sprint13.md).
