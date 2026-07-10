# BeautyOS — Plano de Migração Técnica

**De:** TrançaPro (vertical piloto, monólito SQLite, Expo Web)  
**Para:** BeautyOS v3.0 (Modular Monolith, DDD, Hexagonal, Event-Driven, API First)

Este documento define **o que manter**, **o que refatorar** e **em que ordem**, sem big bang.

---

## Fases de evolução

```
Fase 0 (ATUAL)     Fase A              Fase B              Fase C              Fase D
TrançaPro          BeautyOS Core       Plataforma SaaS     IA Copiloto         Ecossistema
─────────────────────────────────────────────────────────────────────────────────────────
1 tenant           Branding + API v1   Company + RBAC      AI Assistant        Marketplace
SQLite             Consolidar APIs   MySQL + Alembic     Vision v1           Flutter app
Expo Web           Pix real            CRM rico            AI CRM              Enterprise
Rule-based agent   WhatsApp API        Financeiro full     AI Marketing        White label
```

---

## Sprint 01 — Core Platform

### Objetivo BeautyOS

Autenticação · Usuários · Empresas · RBAC · JWT

### Já implementado

- JWT access + refresh (`/auth`)
- Registro e login (`User`, bcrypt)
- Flag `is_superuser` (admin vs cliente)
- Guards no frontend (`AuthGuard`, `AdminGuard`)

### Tarefas de migração

| # | Tarefa | Prioridade | Arquivos / área |
|---|--------|------------|-----------------|
| 1.1 | Criar model `Company` (tenant) | Alta | `models/company.py` |
| 1.2 | Adicionar `company_id` em entidades operacionais | Alta | migrations |
| 1.3 | RBAC: roles `owner`, `professional`, `receptionist`, `customer` | Alta | `core/rbac.py` |
| 1.4 | Unificar `Cliente` + `User` cliente em `Customer` | Média | `customers` module |
| 1.5 | Renomear API: `APP_NAME = "BeautyOS API"`, version `/v1/` | Alta | `config.py`, `main.py` |
| 1.6 | Middleware tenant: resolver `company_id` do JWT | Alta | `dependencies.py` |

### Schema proposto (Company)

```python
# Company
id, nome, slug, segmento (trancista|barbearia|...), plano (free|starter|pro|enterprise)
timezone, logo_url, ativo, created_at

# UserCompany (N:N futuro; 1:1 na Fase A)
user_id, company_id, role
```

### Critério de done

- Todo endpoint operacional filtra por `company_id`
- Admin de outra empresa não vê dados alheios
- Testes de isolamento tenant

---

## Sprint 02 — Agenda Inteligente

### Já implementado

- `AgendaDia` (expediente por data)
- `DisponibilidadeService` (slots 30 min, capacidade única)
- `Schedule` (blocos pós-aprovação)
- `ScheduleStatus.blocked` (modelo existe)

### Tarefas

| # | Tarefa | Prioridade |
|---|--------|------------|
| 2.1 | API admin para bloqueios de agenda | Alta |
| 2.2 | `professional_id` em Schedule/AgendaDia (prep multi-staff) | Média |
| 2.3 | Recorrência de expediente (template semanal) | Média |
| 2.4 | Google Calendar adapter real (substituir mock) | Baixa |
| 2.5 | Cache Redis de slots disponíveis | Média (após MySQL) |

### Renomeação gradual (API v2)

| Legado | BeautyOS |
|--------|----------|
| `Tranca` | `ServiceCategory` |
| `ServiceImage` | `ServiceOffering` |
| `/trancas` | `/v1/catalog/categories` (alias mantém legado) |

---

## Sprint 03 — Reservas + Pagamento

### Já implementado

- Ciclo completo `ReservationStatus`
- Snapshot de preço na reserva
- `/reservations`, `/payments`
- Mock Pix + comprovante manual
- Duplicata legado: `/agenda`, `/pagamentos`

### Tarefas

| # | Tarefa | Prioridade |
|---|--------|------------|
| 3.1 | **Deprecar** `/agenda` e `/pagamentos` — redirecionar para `/reservations` | Alta |
| 3.2 | Adapter `PaymentProvider`: Mock → Mercado Pago → Asaas → Stripe | Alta |
| 3.3 | Webhook confirmação PIX automática (status `pending_approval`) | Alta |
| 3.4 | Idempotência de pagamentos (`transaction_id` único) | Média |
| 3.5 | Expirar `pending_payment` no novo enum (não só legado `pendente`) | Média |

### Manter sem alteração

- Lógica de aprovação admin (diferencial competitivo)
- Fila waitlist + fila operacional
- Snapshot comercial no `Agendamento`

---

## Sprint 04 — CRM

### Já implementado

- `Cliente` com telefone único
- Admin CRM básico (`AdminService.listar_crm_clientes`)
- Histórico via agendamentos

### Tarefas

| # | Tarefa | Prioridade |
|---|--------|------------|
| 4.1 | `CustomerProfile`: tags, preferências, observações | Alta |
| 4.2 | Fotos antes/depois por cliente | Alta |
| 4.3 | Timeline unificada (reservas + pagamentos + notas) | Média |
| 4.4 | `last_visit_at`, `avg_ticket`, `visit_interval_days` | Média |
| 4.5 | Segmentação VIP / inativo (base para AI CRM) | Média |

---

## Sprint 05 — Financeiro

### Já implementado

- `Financeiro` — entradas no confirmar sinal
- Dashboard receita mês

### Tarefas

| # | Tarefa | Prioridade |
|---|--------|------------|
| 5.1 | Despesas (saídas) + categorias | Alta |
| 5.2 | Fluxo de caixa (entradas − saídas) | Alta |
| 5.3 | Comissões por profissional | Média (requer Sprint 01 multi-staff) |
| 5.4 | Relatórios exportáveis (CSV/PDF) | Baixa |

---

## Sprint 06 — Marketplace

**Pré-requisitos:** Sprint 01 (tenant) + 03 (pagamento real) + catálogo genérico

| # | Tarefa |
|---|--------|
| 6.1 | Perfil público da empresa (`/marketplace/companies/{slug}`) |
| 6.2 | Busca + filtros (serviço, preço, segmento) |
| 6.3 | Geolocalização (lat/lng na Company) |
| 6.4 | Reviews e favoritos |
| 6.5 | App cliente (web ou Flutter) consumindo mesma API |

---

## Sprint 07 — Módulos Especializados

Trancista já é o piloto. Extrair configuração por segmento:

```python
# settings por company
segment: trancista | barbearia | manicure | estetica | tattoo
module_config: JSON  # campos extras, terminologia, fluxos
```

| Segmento | Especificidade |
|----------|----------------|
| Trancista | Categoria → Modelo, duração longa, sinal alto |
| Barbearia | Serviços rápidos, fila walk-in |
| Manicure | Combo serviços, materiais |
| Estética | Pacotes, sessões recorrentes |
| Tattoo | Orçamento + sessões múltiplas |

---

## Sprint 08 — Flutter Mobile

**Não reescrever Expo imediatamente.** Sequência:

1. Extrair `@beautyos/api-client` (OpenAPI → TypeScript/Dart)
2. Flutter app profissional: agenda, fila, CRM, push
3. Offline First: cache local de agenda do dia (Hive/SQLite)
4. FCM para notificações

Expo Web permanece até React Admin Web estar pronto (Sprint 10).

---

## Sprint 09 — Marketing

Cupons · Fidelidade · Campanhas · Programa VIP

Integração natural com módulo IA (geração de conteúdo).

---

## Sprint 10 — Analytics

KPIs alvo vs implementação:

| KPI | Fonte de dados | Status |
|-----|----------------|--------|
| Receita | `Financeiro`, `Payment` | Parcial |
| Ticket médio | `Agendamento.valor_total` | Calculável |
| Cancelamentos | `status = cancelled` | OK |
| Clientes ativos | CRM | Parcial |
| MRR / Churn / LTV | Billing SaaS | Futuro |

---

## Sprint 11 — AI Platform

### Evolução do `AgenteService`

```
Hoje                          Alvo
────                          ────
AgentTask (rules)      →      AgentTask + LLM orchestration
NotificationService    →      + WhatsApp real + push
Admin tela agente      →      Chat copiloto (sidebar)
```

### Primeiras function tools (dados já existem)

```python
get_today_schedule(company_id)
get_pending_reservations(company_id)
get_monthly_revenue(company_id)
get_queue_status(company_id)
get_inactive_customers(company_id, days=60)
create_promotion_draft(company_id, params)  # Sprint 09
```

### Estrutura de pastas alvo

```
backend/app/modules/ai/
  domain/
  application/
    assistant_service.py
    vision_service.py
    tools/
  infrastructure/
    openai_client.py
    mcp_server.py
  api/
    router.py
```

---

## Sprint 12 — Enterprise

- Multi-unidade (`Company` pai → filiais)
- White label (domínio, logo, cores via `settings`)
- API pública com API keys
- Plugins / webhooks outbound

---

## Arquitetura v3.0 — reestruturação modular

Ver **`BEAUTYOS_ARCHITECTURE.md`** para detalhes completos.

### Estado atual vs alvo

```
HOJE (Fase A)                    ALVO (Fase B–C)
─────────────                    ───────────────
app/models/          ───────►    modules/*/domain/
app/services/        ───────►    modules/*/application/
app/routers/         ───────►    modules/*/api/
app/integrations/    ───────►    modules/*/infrastructure/adapters/
(chamadas diretas)   ───────►    shared/events/ (Event Bus)
```

### Já iniciado (v3.0)

| Item | Local | Status |
|------|-------|--------|
| Event Bus in-memory | `app/shared/events/` | ✅ |
| Módulo **identity** (DDD completo) | `app/modules/identity/` | ✅ B1 |
| Port PaymentProvider | `app/modules/payments/application/ports/` | ✅ interface |
| Multi-tenant | `Company`, RBAC, JWT | ✅ |
| Shared kernel | `app/shared/kernel/` | ✅ tenant + RBAC |

### Ordem de extração de módulos (Strangler Fig)

```
1. identity/     ← auth, companies, RBAC ✅ CONCLUÍDO (B1)
2. booking/      ← reservations, fila, queue (+ eventos) 🔜 B2
3. catalog/      ← trancas, service_images
4. payments/     ← port + adapters Pix
5. notifications/← reagir a eventos (substituir imports diretos)
6. scheduling/   ← agenda_dia, disponibilidade
7. crm/ · finance/ · ai/
```

### Eventos prioritários

| Evento | Substituir chamada direta |
|--------|---------------------------|
| `reservation.created` | NotificationService.notificar_nova_reserva |
| `payment.deposit.confirmed` | confirmar sinal + finance entry |
| `reservation.approved` | ScheduleService + Google Calendar + notify |

---

Ordem recomendada de extração para `modules/`:

```
1. identity/      (auth, users, companies, rbac)
2. catalog/       (trancas → categories, offerings)
3. booking/       (reservations, fila, queue)
4. scheduling/    (agenda_dia, availability, schedule)
5. payments/      (payments, providers)
6. crm/           (customers)
7. finance/       (ledger)
8. ai/            (agent, llm)
9. notifications/
10. marketplace/  (último)
```

Cada módulo mantém router registrado em `main.py` até eventual split em microserviços.

---

## Migração de infraestrutura

| Etapa | Ação |
|-------|------|
| 1 | Docker Compose: API + MySQL + Redis |
| 2 | Alembic: baseline a partir do schema SQLite |
| 3 | Script dump SQLite → MySQL (dados piloto) |
| 4 | Dual-run em staging; cutover |
| 5 | Celery para notificações e jobs IA |
| 6 | MinIO para arquivos (substituir `/static` local) |
| 7 | Kafka apenas com volume de eventos justificável |

---

## Frontend: caminho Expo → React + Flutter

| Prazo | Ação |
|-------|------|
| **Agora** | Manter Expo; renomear UI para BeautyOS |
| **Fase B** | Admin denso em React + MUI (Vite) |
| **Fase C** | App cliente web (marketplace) |
| **Sprint 08** | Flutter app profissional |
| **Depois** | Descontinuar Expo quando paridade atingida |

---

## Checklist Fase A (próximas 4–6 semanas)

- [ ] Renomear produto para BeautyOS (UI + API + docs) ✅
- [ ] `Company` model + seed empresa demo ✅
- [ ] `company_id` em reservas, clientes, catálogo ✅
- [ ] Deprecar endpoints legado duplicados
- [ ] Integração PIX real (Mercado Pago ou Asaas)
- [ ] WhatsApp Business API (substituir mock)
- [ ] OpenAPI spec publicada (`/openapi.json`) para clientes futuros
- [ ] Git init + CI básico (testes backend)

---

## O que NÃO fazer agora

1. Kubernetes + Kafka no MVP
2. Reescrever todo frontend antes da API v1 estável
3. Marketplace antes de tenant + pagamento
4. AI Vision/pricing antes de catálogo genérico limpo
5. Apagar código TrançaPro — usar aliases e migração gradual

---

## Glossário de transição

| TrançaPro | BeautyOS |
|-----------|----------|
| TrançaPro | BeautyOS (marca) |
| Trança / Categoria | Service Category |
| ServiceImage / Modelo | Service Offering |
| Agendamento | Appointment / Booking |
| Cliente | Customer |
| User (admin) | Professional / Owner |
| Fila | Waitlist |
| QueueEntry | Operational Queue |
| AgenteService | AI Operations (proto) |

---

*Plano de migração BeautyOS v2.0 — revisão julho/2026*
