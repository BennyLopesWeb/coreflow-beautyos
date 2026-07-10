# 15 — SDK

## Public SDK TypeScript (`@coreflow/sdk`) — CF-11 ✅

Pacote: `packages/coreflow-sdk`

```bash
cd packages/coreflow-sdk && npm install && npm run build
```

```typescript
import { CoreFlowClient } from '@coreflow/sdk';

const sdk = new CoreFlowClient(axiosInstance);
await sdk.listCatalogs();
await sdk.createBooking({ customer_id, catalog_id, offering_id, scheduled_at });
await sdk.listMarketplaceListings();
```

Frontend Expo: dependência `file:../packages/coreflow-sdk` + wrapper `frontend/src/services/coreflowService.ts`.

Rotas declaradas em `manifest.yaml` → `sdk.routes`.

## Plugin SDK (interno)

- Manifests: `backend/plugins/{beauty,sports,clinic}/manifest.yaml`
- Template: `backend/plugins/_template/manifest.yaml` 🔜
- Expandido: menus, routes, permissions, ai, events

## Futuro

Plugins · Temas · Dashboards · Integrações · AI Agents · Relatórios · Flutter SDK

Ver [`06-PLUGIN-FRAMEWORK/README.md`](../06-PLUGIN-FRAMEWORK/README.md) · [`20-FUTURE-VISION/README.md`](../20-FUTURE-VISION/README.md)
