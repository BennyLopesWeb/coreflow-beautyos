# ADR-028 — Payment Boundary (Booking ↔ Payments)

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Relacionado** | ADR-009, ADR-025 |

---

## Contexto

Approve booking depende de "sinal pago" (deposit). Payments é bounded context separado. Compartilhamento direto de models viola DDD.

## Decisão

### Fronteira

```
┌─────────────────┐         ┌─────────────────┐
│  Booking Context │         │ Payment Context │
│  Aggregate: Booking│         │ Aggregate: Payment│
└────────┬────────┘         └────────┬────────┘
         │                           │
         │    PaymentQueryPort       │
         │◄──────(read only)─────────│
         │                           │
         │    payment.deposit.confirmed (event)
         │◄──────(async)─────────────│
         │                           │
         │    booking.approved (event)
         │──────────(async)───────►│ (workflow, optional)
```

### O que cruza a fronteira

| Direção | Permitido | Proibido |
|---------|-----------|----------|
| Booking → Payment | Query via `PaymentQueryPort` | Import Payment model/ORM |
| Payment → Booking | Event `payment.deposit.confirmed` | Direct booking status update |
| Shared | `booking_id`, `company_id` as correlation IDs | Shared tables |

### PaymentQueryPort (R2-F2)

| Método | Retorno | Uso |
|--------|---------|-----|
| `is_deposit_confirmed(booking_id, company_id)` | `bool` | Approve gate |
| `get_deposit_status(booking_id)` | `DepositStatus` enum | Admin UI (optional) |

Implementação: `PaymentQueryAdapter` → ACL → legado payment service OR `core_payments`.

### Eventos

| Evento | Publisher | Consumer |
|--------|-----------|----------|
| `payment.deposit.confirmed` | Payments | Workflow, Booking (read model R3) |
| `payment.deposit.failed` | Payments | Notification |
| `booking.approved` | Booking | Workflow, Payments (audit) |

**R2:** Approve uses **synchronous query** (existing behavior parity). Event-driven approve trigger remains workflow responsibility.

### Regra approve (paridade legado)

```
IF booking.status == pending
AND PaymentQueryPort.is_deposit_confirmed(booking_id)
THEN approve()
ELSE 409 Problem Details "deposit_required"
```

### Nada compartilhado diretamente

- ❌ `from app.models.pagamento import Pagamento` in booking module
- ❌ JOIN SQL cross-context in booking repository
- ✅ ACL adapter encapsulates legado

## Matriz de decisão

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Payment logic inside Booking aggregate | ❌ Wrong boundary |
| B | PaymentQueryPort + events | ✅ Escolhida |
| C | Shared "Order" aggregate R2 | ❌ Scope creep |

## Consequências

- F2 implements PaymentQueryPort only — no Payment hexagonal full (R3)
- Paridade cenário 6 (deposit) mandatory

## Referências

- `docs/BoundedContexts.md`
- `docs/DomainRegistry.md`
