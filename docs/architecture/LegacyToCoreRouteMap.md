# Legado / BeautyOS → CoreFlow v1 — Route Map

**Versão:** 1.0 · **Release:** R1-F1  
**API:** `GET /v1/platform/legacy-route-map`  
**Código:** `backend/app/core/legacy_route_map.py`

---

## Camadas API

| Layer | Descrição | Exemplos |
|-------|-----------|----------|
| **legacy** | API PT-BR original | `/agenda`, `/trancas`, `/clientes` |
| **beautyos** | API BeautyOS intermediária | `/reservations`, `/payments`, `/queue` |
| **core** | CoreFlow v1 | `/v1/*` |
| **identity** | Auth e companies | `/auth`, `/companies` |
| **platform** | Governança | `/v1/platform/*` |

---

## Escritas (enforcement)

| Layer | Method | Legado | Core v1 | Domain |
|-------|--------|--------|---------|--------|
| legacy | POST | `/agenda/agendamentos` | `/v1/bookings` | booking |
| legacy | POST | `/agendamentos` | `/v1/bookings` | booking |
| legacy | PUT | `/agendamentos` | `/v1/bookings` | booking |
| legacy | DELETE | `/agendamentos` | `/v1/bookings` | booking |
| legacy | POST | `/fila` | `/v1/waitlist` | waitlist |
| legacy | POST | `/pagamentos/sinal` | `/v1/payments` | payment |
| legacy | POST | `/financeiro/saida` | `/v1/invoices` | invoice |
| beautyos | POST | `/reservations` | `/v1/bookings` | booking |
| beautyos | PUT | `/reservations` | `/v1/bookings` | booking |
| beautyos | POST | `/payments/deposit` | `/v1/payments` | payment |
| beautyos | POST | `/payments/final` | `/v1/payments` | payment |

Fonte: `LEGACY_WRITE_ROUTES` em `core_enforcement.py`.

---

## Leituras principais

| Layer | Method | Legado | Core v1 | Domain |
|-------|--------|--------|---------|--------|
| legacy | GET | `/trancas` | `/v1/catalogs` | catalog |
| legacy | GET | `/clientes` | `/v1/customers` | customer |
| legacy | GET | `/agendamentos` | `/v1/bookings` | booking |
| beautyos | GET | `/reservations` | `/v1/bookings` | booking |
| beautyos | GET | `/payments` | `/v1/payments` | payment |

---

## ACL (RFC-002)

```
Legacy HTTP → Legacy Adapter → Booking Port → Core Module
```

Implementação: `backend/app/shared/acl/booking_port.py`  
Wiring completo: Release 2 (`FEATURE_BOOKING_CORE_ENABLED=true`).

---

## Telemetria

Prometheus (quando `FEATURE_LEGACY_TELEMETRY_ENABLED=true`):

- `coreflow_http_requests_total{layer, method, status_class}`
- `coreflow_http_request_duration_seconds{layer, method}`

Headers resposta:

- `X-CoreFlow-Layer`
- `X-CoreFlow-Successor` (legacy/beautyos)

---

## Rollback R1-F1

```bash
FEATURE_LEGACY_TELEMETRY_ENABLED=false
# Remover middleware: revert PR R1-F1
```

---

*Mapa vivo — atualizar ao adicionar rotas v1 ou sunset legado.*
