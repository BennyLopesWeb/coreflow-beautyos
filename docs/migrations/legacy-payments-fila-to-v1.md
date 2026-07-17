# Migração — Payments / Fila legado → CoreFlow v1

**Release:** `2.1.0-r3-f1` (R3-F1)  
**Escopo:** escritas de payments e fila. Booking já bloqueado desde `2.0.0-beta.1`.

## Antes → Depois

| Legado (bloqueado em staging/prod block) | CoreFlow v1 |
|------------------------------------------|-------------|
| `POST /payments/deposit` | `POST /v1/payments` |
| `POST /payments/final` | `POST /v1/payments` |
| `POST /pagamentos/sinal` | `POST /v1/payments` |
| `POST /fila` | `POST /v1/waitlist` |

Ver também [legacy-booking-to-v1.md](./legacy-booking-to-v1.md).

## Headers de resposta (block)

```
HTTP/1.1 409 Conflict
Deprecation: true
Sunset: Sat, 01 Jan 2028 00:00:00 GMT
Link: </v1/payments>; rel="successor-version"
X-CoreFlow-Enforcement: block
```

## Rollback operacional

```bash
CORE_ENFORCEMENT_MODE=warn
```

Leituras legado (`GET`) **nunca** são bloqueadas neste milestone.  
`POST /financeiro/saida` ainda só recebe warn (não 409).
