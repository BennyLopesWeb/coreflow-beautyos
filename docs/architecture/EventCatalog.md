# CoreFlow — Event Catalog

**Versão:** 1.0 · **Status:** Documentação viva — alinhar com `backend/schemas/events/`

Convenção: `{aggregate}.{action}.v{major}` · payload Avro quando publicado externamente.

---

## Identity

| Evento | Status | Schema | Publisher | Consumers |
|--------|--------|--------|-----------|-----------|
| `user.registered` | ✅ | `identity/domain/events.py` | IdentityService | — |
| `company.created` | ✅ | `identity/domain/events.py` | IdentityService | — |

---

## Booking / Reservation

| Evento | Status | Schema Avro | Publisher | Consumers |
|--------|--------|-------------|-----------|-----------|
| `reservation.created` | ✅ | `reservation.created.v1.avsc` | Legado / booking handlers | workflow, push |
| `booking.created` | ✅ | `booking.created.v1.avsc` | `booking/domain/events.py` | workflow, push |
| `booking.approved` | ✅ | `booking.approved.v2.avsc` | booking handlers | workflow, push |
| `booking.rejected` | ✅ | `booking.rejected.v1.avsc` | booking handlers | workflow |
| `booking.cancelled` | 🔜 | — | — | scheduling, notification |
| `booking.no_show` | 🔜 | — | — | scheduling, CRM |

---

## Payment

| Evento | Status | Schema Avro | Publisher | Consumers |
|--------|--------|-------------|-----------|-----------|
| `payment.deposit.confirmed` | ✅ | `payment.deposit.confirmed.v1.avsc` | payment handlers | booking, workflow |

---

## Customer

| Evento | Status | Schema | Publisher | Consumers |
|--------|--------|--------|-----------|-----------|
| `customer.created` | 🔜 | — | customer module | CRM, AI |
| `customer.updated` | 🔜 | — | — | — |

---

## Worker / Resource / Scheduling

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `worker.created` | 🔜 | scheduling | — |
| `resource.updated` | 🔜 | scheduling | — |
| `schedule.blocked` | 🔜 | scheduling | availability |
| `inventory.updated` | 🔜 | inventory | — |

---

## Order / Invoice / Finance

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `order.created` | 🔜 | order | invoice, workflow |
| `invoice.generated` | 🔜 | invoice | notification, finance |
| `payment.received` | 🔜 | payments | order, workflow |

---

## Notification / Push

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `notification.sent` | 🔜 | push | audit |
| `push.delivered` | 🔜 | push | — |

---

## Workflow

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `workflow.started` | ⚠️ interno | WorkflowEngine | — |
| `workflow.completed` | ⚠️ interno | WorkflowEngine | — |
| `workflow.failed` | ⚠️ interno | WorkflowEngine | — |

---

## AI (planejado)

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `ai.agent.invoked` | 🔜 | AI Platform | audit |
| `ai.recommendation.generated` | 🔜 | AI Platform | CRM |

---

## Infra / Platform

| Evento | Status | Publisher | Consumers |
|--------|--------|-----------|-----------|
| `outbox.dispatched` | ⚠️ interno | OutboxService | — |
| `dlq.message.recorded` | ⚠️ interno | Kafka DLQ | replay worker |
| `canary.promoted` | ⚠️ log | canary promote | rollback worker |
| `canary.rolled_back` | ⚠️ log | canary rollback | — |

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| ✅ | Implementado e testado |
| ⚠️ | Parcial / in-process only |
| 🔜 | Planejado — ver `docs/Backlog.md` EPIC-CORE-002 |

---

## Versionamento

1. **Minor** — campos opcionais adicionados (Avro compatible)
2. **Major** — breaking change → novo subject `.v{N}` + dual consume period
3. Registry: Confluent SR (`backend/app/shared/events/confluent_schema_registry.py`)

---

## Referências de código

| Path | Descrição |
|------|-----------|
| `backend/app/shared/events/domain_event.py` | Base DomainEvent |
| `backend/app/modules/booking/domain/events.py` | Factories booking |
| `backend/schemas/events/avro/*.avsc` | Schemas Avro |
| `backend/schemas/events/*.json` | Schemas JSON |
| `backend/app/shared/events/outbox.py` | Persistência outbox |

---

*Atualizar ao adicionar evento — obrigatório por PR Checklist.*
