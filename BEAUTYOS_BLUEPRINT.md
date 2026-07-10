# BeautyOS — Product Blueprint

**AI-First Platform for Beauty Professionals**

| | |
|---|---|
| **Versão** | 3.0 |
| **Autor** | Benigno Fernandes Lopes |
| **Status do repositório** | Fase A — multi-tenant + base event-driven |
| **Arquitetura** | Ver `BEAUTYOS_ARCHITECTURE.md` |

---

## 1. Visão do Produto

BeautyOS é uma plataforma **SaaS inteligente** destinada à gestão de negócios da área da beleza.

Seu objetivo **não é apenas** organizar agendas ou controlar pagamentos, mas atuar como um **copiloto de negócios**, utilizando Inteligência Artificial para auxiliar profissionais na gestão, atendimento, marketing, relacionamento com clientes e crescimento financeiro.

### Segmentos atendidos (mesma infraestrutura, módulos específicos)

| Segmento | Módulo especializado |
|----------|---------------------|
| Trancistas | ✅ Piloto em desenvolvimento |
| Barbearias | Sprint 07 |
| Salões de Beleza | Sprint 07 + multi-profissional |
| Manicures | Sprint 07 |
| Lash Designers | Sprint 07 |
| Esteticistas | Sprint 07 |
| Maquiadores | Sprint 07 |
| Tatuadores | Sprint 07 |

---

## 2. Missão

Permitir que qualquer profissional da beleza administre seu negócio como uma **empresa de alto desempenho**, utilizando tecnologia e Inteligência Artificial.

---

## 3. Visão de Longo Prazo

Transformar-se no **principal ecossistema digital** para profissionais da beleza da **América Latina**.

Fluxo do ecossistema:

```
Clientes → Marketplace → Profissionais → Agenda → Pagamento
    → IA → CRM → Financeiro → Marketing → Cursos → Comunidade → Produtos
```

---

## 4. Princípios Arquiteturais (v3.0)

### Modular Monolith

Monólito organizado por **bounded contexts** independentes. Um deploy, debug simples, evolução para microsserviços **sem reescrita** quando módulos estiverem desacoplados por portas e eventos.

### Domain-Driven Design (DDD)

Domínio modelado com linguagem ubíqua. Cada módulo: `domain` · `application` · `infrastructure` · `api`.

### Arquitetura Hexagonal (Ports & Adapters)

Núcleo isolado de FastAPI, SQLAlchemy e integrações externas. Ex.: `PaymentProviderPort` → Mock / Mercado Pago / Asaas.

### API First

- Toda regra de negócio existe **exclusivamente na API**.
- Nenhuma regra crítica no frontend.
- Todos os clientes consomem a **mesma API**:
  - React Web
  - Flutter Mobile
  - IA / Agentes
  - WhatsApp
  - Integrações futuras

### AI First

- A IA é **parte da arquitetura**, não um recurso adicional.
- Participa de praticamente todos os módulos.
- Orquestrada como serviço central com tools sobre dados do negócio.

### Mobile First

- O app mobile é a **principal experiência do profissional** no expediente.
- Web completo para gestão, dashboards e operações densas.

### Cloud Native

- Escala horizontal.
- Containers, filas, cache, storage object.

### Multi Tenant

- Uma infraestrutura, milhares de empresas.
- Isolamento lógico por `company_id` em todas as entidades.

### Event-Driven Architecture

- Módulos comunicam-se por **eventos de domínio** (`reservation.created`, `payment.deposit.confirmed`).
- MVP: `InMemoryEventBus` · Produção: RabbitMQ → Kafka.
- Desacopla booking, payments, notifications, IA.

Detalhamento completo: **`BEAUTYOS_ARCHITECTURE.md`**

## 5. Arquitetura Geral

```
                    Internet
                         │
                    API Gateway
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   React Web                          Flutter
        │                                 │
   Marketplace · Admin · Mobile Apps      │
        │                                 │
        └────────────────┬────────────────┘
                         │
                 BeautyOS API (FastAPI)
                         │
         Domain Driven Services
                         │
    MySQL · Redis · Storage · Kafka · RabbitMQ
```

### Pilares estratégicos

| Pilar | Descrição |
|-------|-----------|
| **Modular Monolith** | Velocidade MVP + preparação para escala |
| **DDD + Hexagonal** | Domínio puro; tecnologia nas bordas |
| **API First** | Regras na API; qualquer canal consome os mesmos serviços |
| **Event-Driven** | Comunicação desacoplada entre módulos |
| **AI First** | IA central: decisões, automações, atendimento |
| **Multi Experience** | Web, Mobile, WhatsApp, agentes — mesma API |

---

## 6. Clientes da Plataforma

| Cliente | Público | Funções principais |
|---------|---------|-------------------|
| **Web Admin** | Profissional / gestor | Gestão completa, CRM, financeiro, analytics, IA |
| **Mobile Pro** | Profissional no dia a dia | Agenda, fila, pagamentos, CRM, IA, push |
| **App Cliente** | Consumidor final | Buscar, reservar, pagar, acompanhar, fidelidade |
| **WhatsApp** | Cliente via chat | Atendimento automatizado por IA + reserva + pagamento |

**Exemplo WhatsApp:**

> Cliente: *Quero fazer Box Braids.*  
> IA: identifica serviço, sugere horários, confirma reserva e envia PIX.

---

## 7. Arquitetura dos Módulos (DDD)

Cada módulo é **independente** (domain / application / infrastructure / api):

```
beauty/
  authentication/    # JWT, refresh, sessões
  users/             # Usuários da plataforma
  companies/         # Empresas (tenant)
  professionals/     # Profissionais vinculados à empresa
  customers/         # Clientes finais
  appointments/      # Agenda, reservas, fila, bloqueios
  payments/          # PIX, Stripe, Mercado Pago, Asaas
  crm/               # Perfil, histórico, fotos, tags
  inventory/         # Produtos, consumo, previsão
  marketplace/       # Busca, geo, avaliações, favoritos
  marketing/         # Campanhas, cupons, fidelidade, VIP
  analytics/         # KPIs, dashboards, metas
  notifications/     # Push, e-mail, WhatsApp
  ai/                # Assistente, Vision, Pricing, MCP, RAG
  files/             # Upload, MinIO/S3
  settings/          # Configurações por empresa
  audit/             # Trilha de auditoria
```

### Mapeamento Fase 0 → módulos alvo

| Módulo BeautyOS | Implementação atual (TrançaPro) | Cobertura |
|-----------------|----------------------------------|-----------|
| authentication | `auth`, JWT | ~70% |
| users | `User` | ~50% (sem RBAC) |
| companies | — | 0% |
| professionals | `User.is_superuser` | ~20% |
| customers | `Cliente` | ~60% |
| appointments | `Agendamento`, `Schedule`, `Fila`, `QueueEntry` | ~75% |
| payments | `Payment`, mock Pix | ~40% |
| crm | admin CRM, `status_crm` | ~30% |
| inventory | — | 0% |
| marketplace | — | 0% |
| marketing | — | 0% |
| analytics | dashboard admin básico | ~15% |
| notifications | `NotificationService` mock | ~25% |
| ai | `AgenteService` rule-based | ~10% |
| files | `/static`, comprovantes | ~40% |
| settings | `AgendaDia` | ~20% |
| audit | — | 0% |

---

## 8. Módulo IA (coração da plataforma)

```
                         ┌─────────────┐
                         │  AI Layer   │
                         │ OpenAI/MCP  │
                         └──────┬──────┘
                                │
     ┌──────────┬───────────────┼───────────────┬──────────┐
     │          │               │               │          │
 AI Assistant  Vision      Pricing        CRM Summary  Marketing
     │          │               │               │          │
     └──────────┴───────────────┴───────────────┴──────────┘
                                │
                    Function Tools (API interna)
                                │
              Appointments · CRM · Finance · Analytics
```

| Capacidade | Descrição | Fase |
|------------|-----------|------|
| **AI Assistant** | Chat: "Quem atende hoje?", "Quanto faturei?", "Crie promoção" | Sprint 11 |
| **AI Vision** | Selfie → formato → sugestão → simulação → reserva → pagamento | Sprint 11 |
| **AI Pricing** | Tempo + material + complexidade → preço sugerido | Sprint 11 |
| **AI CRM** | Resumo automático: preferências, periodicidade, produtos | Sprint 11 |
| **AI Marketing** | Stories, Instagram, TikTok, Facebook, WhatsApp | Sprint 09–11 |
| **AI Analytics** | Queda faturamento, inativos, lucratividade, pico | Sprint 10–11 |
| **AI Inventory** | Previsão compras, consumo, ruptura | Sprint 08+ |

**Stack IA:** OpenAI · LangChain (quando necessário) · MCP · RAG · Vision · Embeddings.

**Estado atual:** `AgenteService` executa automações **rule-based** (lembrete pagamento, reativar cliente, fila). Evolui para orquestrador LLM + tools sem descartar tarefas existentes.

---

## 9. Marketplace

Profissionais anunciam serviços. Clientes podem:

- Pesquisar e comparar
- Agendar e pagar
- Avaliar e favoritar
- Geolocalização

**Dependências:** multi-tenant, pagamento real, catálogo genérico, app cliente.

---

## 10. Roadmap (12 Sprints)

| Sprint | Entrega | Status Fase 0 |
|--------|---------|---------------|
| **01** | Core: Auth, Users, Companies, RBAC, JWT | Parcial |
| **02** | Agenda: disponibilidade, bloqueios, recorrência, Google Calendar | Parcial |
| **03** | Reservas + Pagamento: PIX, Stripe, Mercado Pago, Asaas | Parcial |
| **04** | CRM: clientes, fotos, histórico, observações | Início |
| **05** | Financeiro: fluxo caixa, despesas, comissões | Início |
| **06** | Marketplace: busca, geo, avaliações, favoritos | Não iniciado |
| **07** | Módulos especializados (Trancista, Barbearia, …) | Trancista piloto |
| **08** | Mobile Flutter: Android, iOS, offline, push | Não iniciado |
| **09** | Marketing: cupons, fidelidade, campanhas, VIP | Não iniciado |
| **10** | Analytics: KPIs, dashboards, metas | Não iniciado |
| **11** | AI Platform: assistente, Vision, prompt engine | Proto rule-based |
| **12** | Enterprise: white label, franquias, API pública | Não iniciado |

Detalhamento técnico sprint a sprint: ver `BEAUTYOS_MIGRATION.md`.

---

## 11. Modelo de Negócio (SaaS)

| Plano | Incluso |
|-------|---------|
| **Free** | Agenda · até 20 clientes |
| **Starter** | Agenda · CRM · Financeiro |
| **Pro** | Marketplace · IA · Marketing · Analytics |
| **Enterprise** | Multi-unidade · White Label · API · Integrações |

Limites enforced na API (não no frontend).

---

## 12. Diferenciais Competitivos

BeautyOS **não compete só com agendamento**. Combina:

- Gestão de negócios
- Marketplace
- Inteligência Artificial em todos os módulos
- Apps móveis (Flutter)
- Automação WhatsApp
- CRM inteligente
- Marketing automatizado
- Análise preditiva
- Plataforma extensível por módulos

---

## 13. Stack Tecnológica

### Backend (alvo)

| Tecnologia | Uso |
|------------|-----|
| FastAPI | API REST |
| SQLAlchemy 2.x | ORM |
| Alembic | Migrações |
| MySQL | Banco principal |
| Redis | Cache, sessões, slots |
| Celery + RabbitMQ | Jobs assíncronos |
| Kafka | Eventos (escala) |
| MinIO | Arquivos |

### Frontend Web (alvo)

React · TypeScript · Vite · Material UI · TanStack Query · React Hook Form

### Mobile (alvo)

Flutter · Riverpod · GoRouter · Firebase Cloud Messaging · Offline First

### Cloud

Docker · Kubernetes · Traefik · GitHub Actions · Cloudflare

### Fase 0 (repositório atual)

| Camada | Atual | Alvo |
|--------|-------|------|
| Backend | FastAPI + SQLite | MySQL + Redis |
| Frontend | Expo / RN Web | React Web + Flutter |
| IA | Agente rule-based | OpenAI + MCP + tools |

---

## 14. Visão 5 Anos

Evolução de **SaaS → ecossistema digital**:

- Marketplace de serviços e produtos
- Cursos e comunidade
- Programas de fidelidade
- APIs públicas e integrações ERP
- White label para redes e franquias
- Conexão profissionais · clientes · fornecedores · educação · parceiros

---

## 15. Documentos relacionados

| Arquivo | Conteúdo |
|---------|----------|
| `BEAUTYOS_ARCHITECTURE.md` | Arquitetura v3.0: DDD, Hexagonal, Event-Driven, Modular Monolith |
| `BEAUTYOS_MIGRATION.md` | Plano de migração técnica sprint a sprint |
| `DOCUMENTACAO.md` | Regras de negócio e APIs da implementação atual |
| `backups/` | Snapshots do projeto antes de grandes mudanças |

---

*BeautyOS Product Blueprint v3.0 — Benigno Fernandes Lopes*
