# Sprint 11 — SDK TypeScript + Plugins Verticais + Production Enforcement

## Entregas

| Item | Status |
|------|--------|
| Pacote `@coreflow/sdk` (`packages/coreflow-sdk`) | ✅ |
| `CoreFlowClient` — catalogs, bookings, scheduling, marketplace | ✅ |
| Frontend integrado via `file:../packages/coreflow-sdk` | ✅ |
| Plugin `sports` manifest local | ✅ |
| Plugin `clinic` manifest local | ✅ |
| Marketplace: sports/clinic `installable: true` | ✅ |
| `APP_ENV=production` → enforcement `warn` default | ✅ |
| Testes `test_cf11_plugins_sdk.py` | ✅ |
| Versão `1.1.0-sprint11` | ✅ |

## SDK TypeScript

```bash
cd packages/coreflow-sdk && npm install && npm run build
```

```typescript
import { CoreFlowClient } from '@coreflow/sdk';
import api from './config/api';

const sdk = new CoreFlowClient(api);
const catalogs = await sdk.listCatalogs();
const booking = await sdk.createBooking({ ... });
```

Frontend: `frontend/src/services/coreflowService.ts` delega ao SDK.

## Plugins Verticais

| plugin_id | Produto | Terminologia chave |
|-----------|---------|-------------------|
| `beauty` | BeautyOS | Trancista / Trança / Agendamento |
| `sports` | SportsOS | Árbitro / Quadra / Reserva |
| `clinic` | ClinicOS | Médico / Consultório / Consulta |

Manifests: `backend/plugins/{beauty,sports,clinic}/manifest.yaml`

## Production Enforcement (rollout gradual)

Prioridade em `resolve_enforcement_mode()`:

1. `CORE_ENFORCEMENT_ENABLED=true` → **block**
2. `CORE_ENFORCEMENT_MODE` explícito
3. `APP_ENV=staging` → **block**
4. `APP_ENV=production` → **warn** (CF-11)
5. **off**

```bash
APP_ENV=production make run     # warn legado writes por default
CORE_ENFORCEMENT_MODE=block ... # força block em production
```

## Marketplace

```bash
GET  /v1/marketplace/listings   # beauty, sports, clinic instaláveis
POST /v1/marketplace/install    {"plugin_id": "sports"}
```

## Próximo: CF-12

- Deep links mobile
- Push notifications via outbox
- Enforcement `block` em production (fase final)

## Concluído em CF-12

Ver [`Sprint12.md`](./Sprint12.md).
