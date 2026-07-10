# BeautyOS — Documentação da Implementação (Fase 0)

**Vertical piloto:** Trancista · **Blueprint:** v3.0 · **Arquitetura:** Modular Monolith (DDD + Hexagonal + Event-Driven)

Plataforma SaaS AI-First para profissionais da beleza. Nesta fase, o núcleo operacional cobre agendamento, reservas com sinal, fila de espera, fila operacional e CRM básico para **trancistas** (1 profissional / 1 tenant implícito).

Documentos estratégicos:

- `BEAUTYOS_ARCHITECTURE.md` — arquitetura v3.0 (DDD, Hexagonal, Event-Driven)
- `BEAUTYOS_BLUEPRINT.md` — visão de produto, roadmap v3.0
- `BEAUTYOS_MIGRATION.md` — plano de migração técnica sprint a sprint

### Posição no roadmap BeautyOS

| Sprint | Módulo | Cobertura Fase 0 |
|--------|--------|------------------|
| 01 | Core (Auth, Users, RBAC) | ✅ ~90% (módulo identity) |
| 02 | Agenda | Parcial — slots, expediente, schedule |
| 03 | Reservas + Pagamento | Parcial — ciclo completo; Pix mock |
| 04 | CRM | Início — clientes + admin básico |
| 05 | Financeiro | Início — entradas automáticas |
| 11 | IA | Proto — `AgenteService` rule-based |

---

## 1. Stack e arquitetura

| Camada | Fase 0 (atual) | Alvo BeautyOS v2.0 |
|--------|----------------|-------------------|
| **Backend** | FastAPI, SQLAlchemy 2, SQLite | FastAPI, MySQL, Redis, Celery |
| **Autenticação** | JWT (access + refresh), bcrypt | JWT + RBAC + multi-tenant |
| **Frontend Web** | Expo 50, RN Web, TypeScript | React, Vite, MUI, TanStack Query |
| **Mobile** | Expo (web/mobile) | Flutter, offline-first, FCM |
| **IA** | Agente rule-based | OpenAI + MCP + function tools |
| **Deploy local** | Backend `:8000` · Frontend `:8081` | Docker Compose |

**Princípios aplicáveis já hoje:** API First (regras no backend), preparação para AI First (dados estruturados para tools futuras).

### Estrutura de pastas

```
backend/
  app/
    models/       # Entidades SQLAlchemy
    schemas/      # DTOs Pydantic (validação API)
    services/     # Regras de negócio
    routers/      # Endpoints REST
    db/           # Sessão, migração incremental (migrate_schema.py)
frontend/
  app/
    (auth)/       # Login e cadastro
    (tabs)/       # Fluxo cliente
    (admin)/      # Painel profissional
  src/
    services/     # Clientes HTTP (API)
    components/   # UI reutilizável
    contexts/     # Auth, operacional admin
```

### Princípio de modelagem comercial

- **Categoria (`Tranca`)** — apenas agrupa modelos: nome, descrição, imagens, ativo.
- **Modelo (`ServiceImage`)** — toda informação comercial: preço, duração, percentual de sinal, nome, complexidade.
- **Reserva (`Agendamento`)** — snapshot de preços no momento da reserva (não muda se o modelo for alterado depois).

---

## 2. Modelos de domínio

### Categoria — `Tranca`

| Campo | Descrição |
|-------|-----------|
| `nome`, `descricao` | Identificação da categoria |
| `imagens` | URLs de capa (JSON) |
| `ativo` | Visível no catálogo |

### Modelo — `ServiceImage`

| Campo | Descrição |
|-------|-----------|
| `service_id` | FK → categoria |
| `valor_total` | Preço do atendimento |
| `percentual_sinal` | Default 30% (0.30) |
| `valor_sinal` | Calculado: total × percentual |
| `duracao_minutos` | Tempo do serviço |
| `nome`, `descricao`, `nivel_complexidade` | Detalhes do modelo |
| `ativo` | Disponível para reserva |

### Cliente — `Cliente`

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome completo |
| `telefone` | **Único** — chave de identificação |
| `email` | Opcional |

### Usuário — `User` (profissional)

| Campo | Descrição |
|-------|-----------|
| `email`, `password` | Login |
| `nome`, `telefone` | Perfil |
| `is_superuser` | `true` = acesso admin |

### Reserva — `Agendamento`

| Campo | Descrição |
|-------|-----------|
| `cliente_id`, `tranca_id`, `service_image_id` | Quem, categoria, modelo |
| `data_hora` | Horário solicitado |
| `horario_aprovado` | Horário confirmado pela profissional |
| `valor_total`, `valor_sinal`, `valor_restante`, `percentual_sinal` | Snapshot comercial |
| `sinal_pago` | Boolean |
| `comprovante_url` | URL do comprovante de depósito |
| `status` | Ciclo de vida da reserva (ver §4) |
| `status_pagamento` | Estado agregado do pagamento |
| `horario_sugerido`, `mensagem_reagendamento` | Negociação de horário |
| `motivo_rejeicao` | Se rejeitada |

### Fila de espera — `Fila` (waitlist)

Cliente **sem horário confirmado**. Admin avalia e combina horário.

| Campo | Descrição |
|-------|-----------|
| `data` | Data desejada |
| `horario_desejado` | Preferência opcional |
| `posicao` | Ordem FIFO do dia |
| `mesmo_dia` | Flag urgente |
| `agendamento_id` | Preenchido após aprovação |

### Fila operacional — `QueueEntry`

Atendimentos **do dia** após reserva aprovada (ou walk-in urgente).

| Campo | Descrição |
|-------|-----------|
| `posicao` | Ordem de chamada |
| `status` | waiting → called → checked_in → in_service → completed |
| `agendamento_id` | Vínculo com reserva (opcional em urgente) |

### Agenda — `Schedule`

Bloco de tempo na agenda após aprovação da reserva.

| Campo | Descrição |
|-------|-----------|
| `inicio`, `fim` | Intervalo baseado na duração do modelo |
| `status` | scheduled / completed / cancelled |

### Pagamento — `Payment`

| Campo | Descrição |
|-------|-----------|
| `tipo` | `deposit` (sinal), `final_payment`, `refund` |
| `valor`, `status` | Valor e estado |
| `comprovante_url`, `transaction_id` | Comprovante e ID externo |

### Expediente — `AgendaDia`

Configuração por data: horário de abertura/fechamento e se o dia está ativo.

**Padrão** (se não configurado): 08:00–18:00, ativo.

---

## 3. Regras de negócio implementadas

### 3.1 Catálogo e modelos

- Apenas categorias **ativas** aparecem no catálogo.
- Apenas modelos **ativos**, com **preço > 0** e **duração > 0**, podem ser reservados.
- Modelo deve pertencer à categoria selecionada.
- Admin pode cadastrar até **6 fotos por categoria** (galeria de modelos).
- Preço e duração são **somente do modelo**, não da categoria.

### 3.2 Disponibilidade de horários

- Slots gerados a cada **30 minutos** dentro do expediente do dia.
- Duração considerada = duração do **modelo** selecionado (bloqueia vários slots consecutivos).
- Horários no **passado** são indisponíveis.
- **Capacidade única** — um atendimento por vez (salão com uma cadeira).
- Conflito detectado por sobreposição de intervalos com reservas em status que **ocupam vaga**.
- Dia bloqueado (`AgendaDia.ativo = false`) → nenhum horário disponível.
- Reservas legadas `pendente` **sem sinal** há mais de **2 horas** são canceladas automaticamente na consulta de disponibilidade.

### 3.3 Criação de reserva (cliente)

**Validações:**
- Data/hora não pode ser no passado.
- Categoria ativa e modelo válido.
- Horário deve estar na lista de disponíveis.
- Sem conflito com outras reservas ativas.

**Ao criar:**
- Status → `pending_payment`
- Snapshot de preços gravado na reserva.
- Registro de pagamento pendente (tipo `deposit`) criado.
- Notificação enviada à profissional.

**Campos obrigatórios (frontend):**
- Nome completo.
- Telefone (mín. 10 dígitos) **ou** confirmação do telefone se já cadastrado no perfil.
- Data e horário (reserva) ou data (fila).

### 3.4 Pagamento do sinal

1. Cliente pode anexar **comprovante** (JPG, PNG, WEBP, PDF, máx. 5 MB).
2. Comprovante **não confirma** pagamento automaticamente — apenas armazena URL.
3. Admin **confirma sinal** → `sinal_pago = true`, status → `pending_approval`, pagamento → `partially_paid`.
4. Entrada financeira registrada automaticamente.
5. Reserva **permanece visível** para aprovação mesmo após sinal pago.

### 3.5 Aprovação da profissional

**Pré-requisitos para aprovar:**
- Sinal pago (`sinal_pago = true`).
- Status `pending_approval` ou `waiting_time_confirmation`.

**Ao aprovar:**
- Status → `approved`.
- `horario_aprovado` definido.
- Bloco `Schedule` criado na agenda.
- Notificação ao cliente.

**Rejeitar:**
- Status → `rejected`, motivo opcional, schedule cancelado.

**Sugerir novo horário (negociação):**
- Status → `waiting_time_confirmation`.
- `horario_sugerido` + mensagem opcional.
- Cliente aceita → `approved` + schedule atualizado.

### 3.6 Fila de espera (waitlist)

**Entrada:**
- Cliente escolhe data; se não há horários livres ou opta por “atendimento hoje”.
- Posição FIFO automática por data.
- **Um cliente ativo por data** (não pode duplicar na mesma data).

**Gestão admin:**
- **Contactar** → status `contacted`.
- **Aprovar** com horário → cria reserva + vincula `agendamento_id`.
- **Rejeitar/cancelar** → reorganiza posições dos demais.

**Vaga liberada:**
- Ao cancelar reserva, primeiros da fila do dia são notificados (até 3).

### 3.7 Fila operacional (dia do atendimento)

Fluxo: **Chamar → Check-in → Iniciar atendimento → Concluir**

| Ação | Efeito |
|------|--------|
| Chamar | Status `called` |
| Check-in | `checked_in` + reserva `checked_in` |
| Iniciar | `in_service` |
| Concluir | `completed` + reserva `completed` |

Reservas aprovadas do dia podem ser processadas para entrar na fila operacional.

### 3.8 Pagamento final

- Só permitido com reserva em status `completed`.
- Cria pagamento `final_payment`.
- Reserva → `paid`.

### 3.9 Cancelamento

- Reserva → `cancelled`, soft delete.
- Schedule cancelado.
- Opcionalmente sugere vaga liberada à fila de espera.

### 3.10 Cadastro de usuário

- E-mail, nome, senha (mín. 6 caracteres) e **telefone obrigatório** (mín. 10 dígitos).
- Admin: `is_superuser = true` (ex.: `benny007@email.com`).

### 3.11 Painel admin operacional

- **Dashboard** exibe reservas pendentes e fila do dia em tempo real.
- **Badges** nas abas Painel, Reservas e Fila com contagem de pendências.
- Métricas: reservas pendentes, aguardando aprovação, fila hoje, receita do mês.

---

## 4. Status e transições

### Reserva (`ReservationStatus`)

```
pending_payment          → Aguardando pagamento do sinal
pending_approval         → Sinal pago, aguardando profissional
waiting_time_confirmation → Horário sugerido, aguardando cliente
approved                 → Aprovada, na agenda
rejected                 → Rejeitada
in_queue                 → Na fila operacional do dia
checked_in               → Cliente fez check-in
in_service               → Em atendimento
completed                → Atendimento concluído
paid                     → Pagamento final recebido
cancelled                → Cancelada
```

**Fluxo principal:**

```
                    ┌─────────────────┐
                    │ pending_payment │
                    └────────┬────────┘
                             │ confirma sinal
                             ▼
                    ┌─────────────────┐
         ┌─────────│pending_approval │─────────┐
         │         └────────┬────────┘         │
    rejeitar          aprovar            sugerir horário
         │                 │                   │
         ▼                 ▼                   ▼
    rejected          approved      waiting_time_confirmation
                             │                   │
                             │              aceitar horário
                             ▼                   ▼
                        in_queue ◄────────── approved
                             │
                    call → check-in → in_service
                             │
                             ▼
                        completed → paid
```

**Status que ocupam vaga na agenda:**  
`pending_payment`, `pending_approval`, `approved`, `in_queue`, `checked_in`, `in_service` (+ legados `pendente`, `confirmado`).

### Pagamento da reserva (`StatusPagamento`)

`pending_payment` → `partially_paid` (sinal) → `paid` (final) | `cancelled`

### Fila de espera (`StatusFila`)

`waiting` → `contacted` → `approved` | `rejected` | `cancelled`

### Fila operacional (`QueueEntryStatus`)

`waiting` → `called` → `checked_in` → `in_service` → `completed` | `cancelled`

---

## 5. APIs REST

Documentação interativa: **http://localhost:8000/docs**

| Prefixo | Descrição |
|---------|-----------|
| `/auth` | Registro, login, refresh, perfil (`/me` com tenant) |
| `/companies` | Empresas (tenant) — listagem pública, detalhe por slug |
| `/trancas` | Catálogo público; CRUD admin; galeria de modelos |
| `/clientes` | CRUD; busca por telefone |
| `/agenda` | Disponibilidade; CRUD agendamentos (legado) |
| `/reservations` | Ciclo completo de reserva (criar, aprovar, rejeitar, reagendar) |
| `/pagamentos` | Pix mock, comprovante, confirmar sinal (legado) |
| `/payments` | Depósito e pagamento final persistidos |
| `/fila` | Entrada e consulta waitlist; ações admin |
| `/queue` | Fila operacional do dia |
| `/admin` | Dashboard, pagamentos, agenda, CRM, agente IA, expediente |
| `/financeiro` | Resumo e lançamentos |
| `/static` | Imagens e comprovantes |

**Autenticação:** header `Authorization: Bearer <token>`.  
JWT inclui `company_id` e `role` (owner, professional, receptionist, customer).  
**Tenant público:** header `X-Company-Slug` ou query `?company=salao-demo` (default: `salao-demo`).  
**Admin:** superuser legado **ou** papel RBAC administrativo no tenant.

---

## 6. Telas e fluxos (frontend)

### Cliente — `(tabs)`

| Tela | Função |
|------|--------|
| Início | Dashboard cliente |
| Catálogo | Lista categorias |
| Detalhe categoria | Modelos com preço individual |
| Agendar | Data, horário, dados, comprovante ou fila |
| Agenda | Minhas reservas |
| Fila | Posição na fila de espera do dia |

**Fluxo típico:** Catálogo → Categoria → Modelo → **Reservar** → Preencher dados → Confirmar ou entrar na fila.

### Admin — `(admin)`

| Tela | Função |
|------|--------|
| Painel | Métricas + reservas/fila pendentes com ações rápidas |
| Catálogo | CRUD categorias e modelos |
| Reservas | Aprovar, rejeitar, confirmar sinal, sugerir horário |
| Pagamentos | Lista de sinais e comprovantes |
| Agenda | Visão de agendamentos |
| Fila | Waitlist: contactar, aprovar, rejeitar |
| Atendimento | Fila operacional do dia |
| CRM | Clientes e métricas |
| Agente IA | Automações |

---

## 7. Como executar

### Backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend (web)

```bash
cd frontend
npm run typecheck
EXPO_PUBLIC_API_URL=http://localhost:8000 npm run build:web
npx serve -s dist -l 8081
```

Acesse: **http://localhost:8081**

### Credenciais de teste

| Perfil | E-mail | Senha |
|--------|--------|-------|
| Admin | `benny007@email.com` | `123456` |
| Cliente | `benny@email.com` | `123456` |

---

## 8. Integrações (MVP / mock)

| Integração | Estado |
|------------|--------|
| Pix | Mock (`PIX_MOCK_ENABLED`) |
| WhatsApp | Mock (notificações simuladas) |
| Google Calendar | Mock (evento ao aprovar reserva legado) |
| Notificações | Log em `notification_logs` |

---

## 9. Observações técnicas

- **Três camadas de API coexistem:** legado (`/agenda`, `/pagamentos`), BeautyOS (`/reservations`, `/payments`) e **CoreFlow v1** (`/v1/catalogs`, `/v1/bookings`, `/v1/plugins`). Telas admin usam legado/BeautyOS; metamodelo v1 espelha o legado via Strangler Fig.
- **SQLite** com migração incremental em `backend/app/db/migrate_schema.py` (executada no startup).
- **Enums** persistidos como string (`.value`) para compatibilidade SQLite.
- **Timezone:** frontend envia data/hora local (`YYYY-MM-DDTHH:mm:ss`) para evitar deslocamento UTC.

---

## 11. Multi-tenant (Fase A — Sprint 01)

### Company (tenant)

| Campo | Descrição |
|-------|-----------|
| `nome`, `slug` | Identificação pública (`salao-demo`) |
| `segmento` | trancista, barbearia, salao, … |
| `plano` | free, starter, pro, enterprise |
| `timezone` | Fuso IANA (default America/Sao_Paulo) |

### RBAC — `UserCompany`

| Papel | Permissões |
|-------|------------|
| `owner` | Acesso total ao negócio |
| `professional` | Agenda, catálogo, CRM, financeiro |
| `receptionist` | Reservas, fila, clientes |
| `customer` | Reservas próprias |

Entidades com `company_id`: Tranca, Cliente, Agendamento, Fila, AgendaDia, Schedule, QueueEntry, Financeiro, AgentTask.

## 12. Módulo Identity (v3.0 — DDD)

Estrutura em `backend/app/modules/identity/`:

```
identity/
  domain/           constants, events (user.registered, company.created)
  application/      IdentityApplicationService, ports, handlers
  infrastructure/   SqlAlchemy repos, JwtTokenService
  api/              auth_router, companies_router, deps
```

`AuthService` e `CompanyService` legados delegam a `IdentityApplicationService`.

---

## 13. CoreFlow Platform (Sprint 0–3)

Evolução para plataforma SaaS com plugins. BeautyOS Trancista = plugin `beauty` (empresa demo `salao-demo`).

| Sprint | Entrega | Estado |
|--------|---------|--------|
| CF-0 | Plugin Loader, `GET /v1/plugins`, metamodelo conceitual | ✅ |
| CF-1 | Catalog/Offering/Booking + sync legado + API v1 + CQRS | ✅ |
| CF-2 | Location/Worker/Resource/ScheduleBlock + scheduling engine + Alembic | ✅ |
| CF-3 | MySQL Docker + frontend v1 availability + Sunset legado | ✅ |
| CF-4 | Scheduling Engine + Resource Engine + conflict API | ✅ |
| CF-5 | core_customers + Outbox + booking v1 frontend | ✅ |
| CF-6 | core_payments + OpenTelemetry + CI MySQL | ✅ |
| CF-7 | core_waitlist + BeautyAgent + manifest SDK | ✅ |
| CF-8 | Workflow + AI LLM + Core Enforcement | ✅ |
| CF-9 | Order/Invoice + Workflow editor + enforcement gradual | ✅ |
| CF-10 | Asset/Inventory + Marketplace + staging enforcement | ✅ |
| CF-11 | SDK TypeScript + plugins sports/clinic + production warn | ✅ |
| CF-12 | Deep links + push outbox + production block | ✅ |
| CF-13 | Expo Push API + universal links + RabbitMQ worker | ✅ |
| CF-14 | Well-known hosting + Expo Notifications + Kafka | ✅ |
| CF-15 | CDN well-known + EAS Build + Schema Registry | ✅ |
| CF-16 | Confluent SR + CDN multi-plugin + EAS CI/CD | ✅ |
| CF-17 | EAS white-label + Avro completo + CDN S3 sync | ✅ |
| CF-18 | EAS Submit + Avro evolution + CloudFront behaviors | ✅ |
| CF-19 | EAS Update OTA + Kafka DLQ + Terraform CDN | ✅ |
| CF-20 | DLQ replay backoff + EAS rollout + Terraform CI | ✅ |
| CF-21 | DLQ handler replay + EAS canary + Terraform pipeline | ✅ |
| CF-22 | Prometheus DLQ + canary auto-promote + Terraform drift | ✅ |
| CF-23 | Grafana dashboards + canary rollback + Terraform OPA | ✅ |
| CF-24 | Alertmanager rules + rollback worker + Terraform Sentinel | ✅ |
| CF-25 | PagerDuty/Opsgenie + canary DB persist + TFC policy set | ✅ |

### Metamodelo (tabelas genéricas)

| CoreFlow | Tabela | Legado |
|----------|--------|--------|
| Catalog | `core_catalogs` | `trancas` |
| Offering | `core_offerings` | `service_images` |
| Booking | `core_bookings` | `agendamentos` |
| Location | `core_locations` | salão implícito (1 por tenant) |
| Worker | `core_workers` | `UserCompany` (owner/professional) |
| Resource | `core_resources` | cadeira implícita (capacidade 1) |
| ScheduleBlock | `core_schedule_blocks` | `schedules` |

`LegacySyncService` e `SchedulingLegacySyncService` sincronizam legado → metamodelo no bootstrap (`init_db`).

### API v1

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/v1/plugins` | Lista plugins instalados |
| GET | `/v1/plugins/{id}` | Manifest do plugin |
| GET | `/v1/plugins/config/by-company/{slug}` | Config UI por tenant |
| GET | `/v1/catalogs` | Catálogos do tenant |
| GET | `/v1/catalogs/{id}/offerings` | Ofertas do catálogo |
| POST | `/v1/bookings` | Cria reserva (CQRS → `ReservationService`) |
| POST | `/v1/bookings/{id}/approve` | Aprova reserva (admin, emite `booking.approved`) |
| POST | `/v1/bookings/{id}/reject` | Rejeita reserva (admin, emite `booking.rejected`) |
| GET | `/v1/bookings` | Lista reservas do tenant |
| GET | `/v1/locations` | Unidades físicas |
| GET | `/v1/workers` | Profissionais |
| GET | `/v1/resources` | Recursos reserváveis |
| GET | `/v1/scheduling/availability` | Slots disponíveis (engine genérico) |
| GET | `/v1/customers` | Clientes genéricos (admin) |
| GET | `/v1/payments` | Pagamentos genéricos (admin) |
| GET | `/v1/waitlist` | Fila de espera genérica (admin) |
| POST | `/v1/ai/analyze` | Análise BeautyAgent (admin) |
| GET | `/v1/ai/tasks` | Tarefas do agente IA (admin) |
| GET | `/v1/workflows/runs` | Auditoria de execuções workflow (admin) |
| GET | `/v1/workflows/definitions` | Definições YAML para editor admin |
| PATCH | `/v1/workflows/definitions/{id}` | Habilita/desabilita workflow |
| GET | `/v1/orders` | Pedidos comerciais genéricos (admin) |
| GET | `/v1/invoices` | Faturas/recibos genéricos (admin) |
| GET | `/v1/assets` | Ativos/insumos genéricos (admin) |
| GET | `/v1/inventory` | Níveis de estoque genéricos (admin) |
| GET | `/v1/marketplace/listings` | Catálogo marketplace cloud |
| POST | `/v1/marketplace/install` | Instala plugin no tenant (admin) |
| POST | `/v1/devices/register` | Registra token push Expo (autenticado) |
| GET | `/v1/outbox/status` | Status outbox pending/failed (admin) |
| POST | `/v1/outbox/replay` | Reprocessa eventos pendentes (admin) |
| GET | `/v1/mobile/well-known/preview` | Preview config Universal/App Links |
| GET | `/.well-known/apple-app-site-association` | AASA iOS Universal Links |
| GET | `/.well-known/assetlinks.json` | Android App Links |
| GET | `/v1/mobile/cdn/manifest` | Manifest deploy CDN |
| POST | `/v1/mobile/well-known/export` | Exporta .well-known para disco (admin) |
| GET | `/v1/events/schemas` | Lista JSON Schemas Kafka |
| GET | `/v1/events/schema-registry/health` | Health Confluent Schema Registry |
| GET | `/v1/mobile/cdn/plugins` | Config CDN mobile por plugin |
| POST | `/v1/mobile/well-known/export-all` | Export CDN multi-tenant (admin) |
| GET | `/v1/mobile/eas/profiles` | Perfis EAS white-label por plugin |
| GET | `/v1/mobile/eas/profiles/{plugin_id}` | Perfil EAS de um plugin |
| POST | `/v1/mobile/eas/generate` | Gera frontend/eas.plugins.json (admin) |
| POST | `/v1/mobile/cdn/sync-s3` | Sync CDN → S3 + CloudFront (admin) |
| GET | `/v1/events/schemas/avro` | Lista schemas Avro locais |
| GET | `/v1/events/schemas/avro/coverage` | Cobertura Avro vs JSON |
| POST | `/v1/events/schemas/avro/register-evolved` | Registra versão evoluída Avro (admin) |
| GET | `/v1/mobile/eas/submit/profiles` | Perfis EAS Submit por plugin |
| POST | `/v1/mobile/eas/submit/generate` | Gera frontend/eas.submit.json (admin) |
| GET | `/v1/mobile/cdn/cloudfront-behaviors` | CloudFront cache behaviors por tenant |
| POST | `/v1/mobile/cdn/terraform/export` | Export terraform.tfvars.json (admin) |
| GET | `/v1/mobile/eas/update/channels` | Canais EAS Update OTA por plugin |
| POST | `/v1/mobile/eas/update/generate` | Gera frontend/eas.update.json (admin) |
| GET | `/v1/events/dlq` | Lista dead-letter queue Kafka |
| GET | `/v1/events/dlq/stats` | Estatísticas DLQ |
| POST | `/v1/events/dlq/replay-auto` | Replay DLQ em lote com backoff (admin) |
| POST | `/v1/events/dlq/{id}/replay` | Replay manual DLQ (`mode=handler\|republish`) |
| GET | `/v1/mobile/eas/update/rollout/{plugin_id}` | Plano rollout OTA gradual |
| GET | `/v1/mobile/eas/update/canary/{plugin_id}` | Plano canary OTA por segmento |
| GET | `/v1/mobile/eas/update/canary/{plugin_id}/segments` | Segmentos canary do plugin |
| GET | `/v1/mobile/cdn/terraform/backend` | Config remote state S3 |
| GET | `/v1/mobile/cdn/terraform/pipeline` | Pipeline dev → staging → prod |
| GET | `/v1/events/dlq/metrics` | Resumo métricas Prometheus DLQ |
| GET | `/metrics` | Exposição Prometheus (text/plain) |
| GET | `/v1/mobile/eas/update/canary/{plugin_id}/health` | Health check canary por segmento |
| POST | `/v1/mobile/eas/update/canary/{plugin_id}/promote` | Auto-promote canary → production (admin) |
| GET | `/v1/mobile/eas/update/canary/{plugin_id}/rollback/evaluate` | Avalia rollback canary |
| POST | `/v1/mobile/eas/update/canary/{plugin_id}/rollback` | Rollback canary → branch anterior (admin) |
| GET | `/v1/events/grafana/dashboard/dlq` | Preview dashboard Grafana DLQ |
| POST | `/v1/events/grafana/dashboard/dlq/export` | Export dashboard + provisioning (admin) |
| GET | `/v1/events/alertmanager/dlq` | Manifest regras alerta DLQ |
| POST | `/v1/events/alertmanager/dlq/export` | Export rules Prometheus + alertmanager.yml (admin) |
| GET | `/v1/mobile/eas/update/canary/promotions` | Promoções canary ativas persistidas (admin) |
| GET | `/v1/mobile/cdn/terraform/cloud/policy-set` | Policy set Terraform Cloud OPA+Sentinel |
| POST | `/v1/mobile/cdn/terraform/cloud/policy-set/export` | Export policy-set.json (admin) |
| POST | `/v1/mobile/eas/update/canary/rollback/scan` | Scan rollback canary automático (admin) |
| GET | `/v1/mobile/cdn/terraform/sentinel` | Manifest políticas Sentinel enterprise |
| GET | `/v1/mobile/cdn/terraform/sentinel/{environment}` | Avalia Sentinel por ambiente (admin) |
| GET | `/v1/mobile/cdn/terraform/policy` | Manifest políticas OPA |
| GET | `/v1/mobile/cdn/terraform/policy/{environment}` | Avalia políticas tfvars (admin) |
| GET | `/v1/mobile/cdn/terraform/drift` | Drift config/plan por ambiente (admin) |
| GET | `/v1/mobile/cdn/terraform/drift/all` | Drift config todos ambientes (admin) |
| POST | `/v1/mobile/cdn/terraform/pipeline/export` | Export multi-ambiente + pipeline.json (admin) |
| POST | `/v1/scheduling/conflicts` | Detecção de conflito em resource |

### Alembic

Revisions `cf001` … `cf010_canary_promotions`. Dev: `make migrate`; MySQL Docker: `make docker-mysql-up`; produção: `make alembic-upgrade`.

### Core Enforcement (Fase B)

`CORE_ENFORCEMENT_MODE=off|warn|block` — modo gradual (default `off`). `APP_ENV=staging` e `APP_ENV=production` forçam `block` (CF-12). Override explícito sempre prevalece.

### Push mobile + Deep links (CF-12/13/14)

Tokens em `core_device_tokens`. Push via `ExpoPushClient`. CDN multi-tenant por plugin (`PluginCdnService`). EAS white-label (`EasWhitelabelService`). Confluent Avro completo. CDN S3 sync (`CdnS3SyncService`). CI: `mobile-eas.yml`, `cdn-sync.yml`.

### SDK TypeScript (`@coreflow/sdk`)

Pacote em `packages/coreflow-sdk` — `CoreFlowClient` para catalogs, bookings, scheduling e marketplace. Frontend Expo consome via `frontend/src/services/coreflowService.ts`.

### Plugins verticais

Manifests locais: `beauty`, `sports`, `clinic` em `backend/plugins/*/manifest.yaml`. Marketplace permite instalar sports/clinic no tenant.

### Depreciação legado (Sunset RFC 8594)

Rotas `/trancas`, `/agenda/*`, `/reservations` etc. retornam headers `Sunset`, `Deprecation` e `Link` apontando para sucessoras v1. Config: `LEGACY_SUNSET_ENABLED`.

### Outbox (eventos)

Tabela `core_event_outbox` — eventos `booking.created`, `booking.approved`, `payment.deposit.confirmed` etc. Workflow YAML reage via `WorkflowEngine`.

### Frontend CoreFlow v1

`agendamentoService` e `coreflowService` usam `@coreflow/sdk` com fallback legado. Flag: `EXPO_PUBLIC_USE_COREFLOW_V1`.

Documentação SAB: `docs/04-SPRINTS/Sprint00.md` … `Sprint20.md`, `docs/06-ADR/ADR001-metamodel.md`.

---

## 14. Glossário

| Termo | Significado no sistema |
|-------|------------------------|
| **Categoria / Trança** | Grupo de modelos (ex.: Box Braids) |
| **Modelo / ServiceImage** | Variante com preço e duração (ex.: Modelo 1 — R$ 600) |
| **Reserva / Agendamento** | Compromisso com horário e snapshot de preço |
| **Fila de espera** | Lista FIFO sem horário confirmado |
| **Fila operacional** | Ordem de atendimento no dia |
| **Sinal** | Depósito parcial (default 30%) para confirmar reserva |
| **Schedule** | Bloco reservado na agenda após aprovação |
| **Catalog / Offering / Booking** | Entidades genéricas CoreFlow (mapeiam Trança / Modelo / Agendamento) |
| **Location / Worker / Resource** | Scheduling genérico (unidade, profissional, cadeira/recurso) |
| **ScheduleBlock** | Bloco genérico na agenda (espelha `Schedule`) |
| **Plugin** | Vertical de negócio registrada no CoreFlow (ex.: `beauty`) |

---

*Documento gerado com base no código da Fase 0 (BeautyOS · vertical Trancista). Última revisão: julho/2026.*
