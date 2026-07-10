# ADR-009 — Booking Domain Pure

| Campo | Valor |
|-------|-------|
| **Status** | ✅ Aceito |
| **Data** | 2026-07-09 |
| **RFC** | [RFC-003](../rfc/RFC-003-CoreDomainConsolidation.md) |
| **Substitui** | Delegação implícita via ReservationService |
| **Relacionado** | ADR-024, ADR-025, ADR-026, ADR-028, ADR-029 |

---

## Contexto

Booking é bounded context central. Hoje commands CQRS delegam a `ReservationService` (legado). A Constituição exige aggregate root no core com linguagem ubíqua **Booking** (não Agendamento/Reservation).

## Decisão

### Aggregate Root: `Booking`

| Elemento | Tipo | Descrição |
|----------|------|-----------|
| **Booking** | Aggregate Root | Reserva de offering por customer em slot de resource/worker |
| **BookingLine** | Entity (child) | Linha com offering_id, duration, price snapshot |
| **BookingStatus** | Value Object (enum) | Estado do ciclo de vida — ver ADR-026 |
| **TimeSlot** | Value Object | `starts_at`, `ends_at`, timezone IANA |
| **Money** | Value Object | `amount`, `currency` (ISO 4217) |
| **BookingId** | Value Object | UUID v4 |
| **LegacyReference** | Value Object | `legacy_id`, `sync_status` — projeção legado |

### Limites do Aggregate

**Dentro:**
- Estado e transições (pending → approved → …)
- Invariantes de slot e status
- Emissão de domain events (`booking.*`)
- Referências por ID: `customer_id`, `resource_id`, `worker_id`, `offering_id`, `company_id`

**Fora (via Port):**
- Persistência (`CoreBookingRepository`)
- Disponibilidade (`SchedulingPort` → `ResourcePort`)
- Pagamento (`PaymentQueryPort`)
- Sync legado (`LegacyBookingPort`)
- Publicação eventos (`DomainEventPublisher` / outbox)

### Invariantes

| ID | Regra |
|----|-------|
| INV-B1 | `company_id` obrigatório — tenant isolation |
| INV-B2 | `starts_at < ends_at` |
| INV-B3 | Não criar booking em slot indisponível (SchedulingPort) |
| INV-B4 | Approve só se status = `pending` e deposit rule satisfied (PaymentQueryPort) |
| INV-B5 | Reject só se status = `pending` |
| INV-B6 | Cancel permitido em `pending`, `approved` (R2); completed/no_show R3+ |
| INV-B7 | Uma transição por vez — optimistic lock via `version` |
| INV-B8 | Domain events só após persistência bem-sucedida (outbox) |

### Estados válidos (R2)

Ver **ADR-026** para máquina completa. R2 implementa: `pending`, `approved`, `rejected`, `cancelled`.

### Application Layer

| Componente | Responsabilidade |
|------------|------------------|
| `CreateBookingCommand` / Handler | Orquestra create |
| `ApproveBookingCommand` / Handler | Orquestra approve |
| `RejectBookingCommand` / Handler | Orquestra reject |
| `CancelBookingCommand` / Handler | Orquestra cancel (F2b) |
| `BookingApplicationService` | Coordena ports; **não** contém regra de domínio |

### Domain Layer

| Componente | Responsabilidade |
|------------|------------------|
| `Booking` (aggregate) | Invariantes, transições, events |
| `BookingDomainService` | Lógica que envolve múltiplos aggregates (raro) |
| Domain Events | `BookingCreated`, `BookingApproved`, etc. |

### Ports (obrigatórios)

| Port | Direção | Implementação |
|------|---------|---------------|
| `CoreBookingRepository` | Out | SQLAlchemy adapter |
| `SchedulingPort` | Out | LegacySchedulingAdapter → ResourceSchedulingAdapter |
| `PaymentQueryPort` | Out | PaymentQueryAdapter |
| `LegacyBookingPort` | Out | `LegacyBookingAdapter` (ACL) |
| `CatalogQueryPort` | Out | Catalog adapter (F3b) |
| `CustomerQueryPort` | Out | Customer adapter (F3b) |

### Proibido

- Import `ReservationService`, `LegacySyncService` em `application/commands/`
- ORM/SQLAlchemy em `domain/`
- Regra de deposit em Booking aggregate (consulta Payment context)

## Matriz de decisão — ReservationService

| Alt | Descrição | Decisão |
|-----|-----------|---------|
| A | Manter ReservationService como facade | ❌ Viola hexagonal |
| B | Booking aggregate + ACL adapter | ✅ Escolhida |
| C | Booking como anemic model + service legado | ❌ Viola DDD |

## Consequências

- Commands refatorados em R2-F0.5 → F2
- Testes paridade obrigatórios
- Eventos canônicos `booking.*`

## Referências

- `docs/DomainRegistry.md` — Booking context
- `docs/EventStorming.md`
- `backend/app/shared/acl/booking_port.py`
