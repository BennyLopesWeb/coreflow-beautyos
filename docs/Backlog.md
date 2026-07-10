# CoreFlow Platform — Backlog

**Versão:** 1.0 · **Data:** 2026-07-09  
**Classificação:** MoSCoW (Must · Should · Could · Won't)  
**Tipos:** Epic · Feature · Story · Task · Bug · Spike · Débito Técnico

Legenda status: 🔜 Planejado · ⏳ RFC/ADR · 🚧 Em progresso · ✅ Done

---

## Must Have

### EPIC-GOV-001 — Governança Arquitetural

| ID | Tipo | Item | Status |
|----|------|------|--------|
| GOV-F1 | Feature | Estrutura docs/ (architecture, adr, rfc, roadmap) | ✅ |
| GOV-F2 | Feature | ArchitectureEvolutionPlan + Backlog + Roadmap 12M | ✅ |
| GOV-S1 | Story | RFC-001 Governança — aprovação stakeholder | ⏳ |
| GOV-S2 | Story | ADR-003 + ADR-004 — aprovação | ⏳ |
| GOV-T1 | Task | PR Checklist adotado em reviews | 🔜 |

### EPIC-CORE-001 — API First & Sunset Legado

| ID | Tipo | Item | MoSCoW | RFC |
|----|------|------|--------|-----|
| CORE-F1 | Feature | Mapa rotas legado → v1 + documentação | Must | RFC-002 F1 |
| CORE-F2 | Feature | Métricas hits por rota legado (Prometheus) | Must | RFC-002 F1 |
| CORE-F3 | Feature | Core enforcement warn → block gradual | Must | RFC-002 |
| CORE-S1 | Story | Sunset headers RFC 8594 em rotas legado | Must | RFC-002 |
| CORE-S2 | Story | Migrar frontend admin bookings → SDK v1 | Must | RFC-002 F3 |
| CORE-D1 | Débito | Três APIs paralelas | Must | ADR-004 |

### EPIC-CORE-002 — Event Catalog & Event-Driven

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| EVT-F1 | Feature | Event Catalog completo documentado | Must |
| EVT-F2 | Feature | Versionamento semver eventos Avro | Must |
| EVT-S1 | Story | Documentar booking.*, payment.*, identity.* | Must |
| EVT-S2 | Story | Handler registry documentado | Must |

### EPIC-CORE-003 — Booking Domain Puro

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| BKG-F1 | Feature | CreateBooking sem ReservationService legado | Must |
| BKG-F2 | Feature | Approve/Reject booking no core | Must |
| BKG-S1 | Story | Testes paridade legado vs v1 | Must |
| BKG-S2 | Story | Domain events booking.created v1 only | Must |
| BKG-D1 | Débito | Commands delegam ao legado | Must |

---

## Should Have

### EPIC-HEX-001 — Hexagonal & Repositories

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| HEX-F1 | Feature | Repository + port em catalog | Should |
| HEX-F2 | Feature | Repository + port em customer | Should |
| HEX-F3 | Feature | Repository + port em scheduling | Should |
| HEX-F4 | Feature | Repository + port em booking | Should |
| HEX-S1 | Story | Template port/adapter documentado | Should |

### EPIC-SCH-001 — Scheduling Engine v2

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| SCH-F1 | Feature | Remover LegacySchedulingAdapter | Should |
| SCH-F2 | Feature | Recurring booking rules | Should |
| SCH-F3 | Feature | No-show detection + evento | Should |
| SCH-F4 | Feature | Cancellation policies genéricas | Should |
| SCH-S1 | Story | Integração waitlist ↔ scheduling | Should |

### EPIC-RES-001 — Resource Engine v2

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| RES-F1 | Feature | Resource hierarchy (parent/child) | Should |
| RES-F2 | Feature | Resource types via plugin manifest | Should |
| RES-S1 | Story | Multi-resource booking | Should |

### EPIC-AI-001 — AI Platform

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| AI-F1 | Feature | AI Provider Registry | Should |
| AI-F2 | Feature | Prompt Engine | Should |
| AI-F3 | Feature | Agent framework genérico | Should |
| AI-S1 | Story | Mover BeautyAgent → plugin beauty | Should |
| AI-S2 | Story | Tools API sobre booking/customer | Should |
| AI-D1 | Débito | BeautyAgent no core module | Should |

### EPIC-OBS-001 — Observabilidade Runtime

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| OBS-F1 | Feature | Docker Compose Prometheus+Grafana+AM | Should |
| OBS-F2 | Feature | Audit trail tabela + API | Should |
| OBS-S1 | Story | CF-26 Slack receivers | Should |
| OBS-S2 | Story | OpenTelemetry default dev stack | Should |

### EPIC-SEC-001 — Segurança

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| SEC-F1 | Feature | Rate limiting middleware | Should |
| SEC-F2 | Feature | Audit log auth actions | Should |
| SEC-S1 | Story | OWASP checklist docs/13-SECURITY | Should |

### EPIC-FE-001 — Frontend SDK Migration

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| FE-F1 | Feature | Substituir agendamentoService → coreflow SDK | Should |
| FE-F2 | Feature | Substituir trancaService → v1 catalogs | Should |
| FE-F3 | Feature | Substituir reservationService → v1 bookings | Should |
| FE-S1 | Story | Testes componente AuthGuard | Should |

---

## Could Have

### EPIC-PLG-001 — Plugin Engine v2

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| PLG-F1 | Feature | Plugin Context runtime | Could |
| PLG-F2 | Feature | Plugin permissions no manifest | Could |
| PLG-F3 | Feature | Plugin menus/dashboard config | Could |
| PLG-F4 | Feature | Plugin SDK CLI geradores | Could |

### EPIC-MKT-001 — Marketplace

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| MKT-F1 | Feature | Install plugin per tenant | Could |
| MKT-F2 | Feature | Billing stub | Could |
| MKT-F3 | Feature | Reviews/ratings | Could |

### EPIC-MOB-001 — Mobile Offline

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| MOB-S1 | Spike | Sync engine Expo + SQLite local | Could |
| MOB-S2 | Spike | Queue offline mutations | Could |

### EPIC-WF-001 — Workflow Visual

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| WF-F1 | Feature | Editor visual workflow | Could |
| WF-S1 | Story | Action catalog padronizado | Could |

### EPIC-TEN-001 — Multi-Tenant Avançado

| ID | Tipo | Item | MoSCoW |
|----|------|------|--------|
| TEN-F1 | Feature | Business entity (holding) | Could |
| TEN-F2 | Feature | Branch / Department | Could |
| TEN-F3 | Feature | White-label theming API | Could |

---

## Won't Have (este ciclo 12M)

| ID | Item | Motivo |
|----|------|--------|
| WNT-1 | Rewrite greenfield v2 | Viola ADR-004 |
| WNT-2 | Microsserviços por módulo | Modular monolith suficiente |
| WNT-3 | Migrar Expo → Flutter | Custo; Expo funcional |
| WNT-4 | Remover API legado abruptamente | Breaking piloto |
| WNT-5 | Schema-per-tenant DB | Complexidade prematura |

---

## Bugs & Spikes abertos

| ID | Tipo | Item | Prioridade |
|----|------|------|------------|
| BUG-1 | Bug | FastAPI on_event deprecated → lifespan | Baixa |
| BUG-2 | Bug | SQLAlchemy declarative_base deprecated | Baixa |
| SPIKE-1 | Spike | pytest-cov + coverage gate CI | Média |
| SPIKE-2 | Spike | Frontend Detox E2E viabilidade | Baixa |
| SPIKE-3 | Spike | RAG architecture para AI Platform | Média |

---

## Débitos Técnicos (consolidado)

Ver `docs/ArchitectureAssessment.md` §25 — DT-01 a DT-18.

| ID | Débito | Severidade | Epic |
|----|--------|------------|------|
| DT-01 | Três APIs paralelas | Alta | EPIC-CORE-001 |
| DT-02 | Regras no legado | Alta | EPIC-CORE-003 |
| DT-05 | Frontend APIs mistas | Alta | EPIC-FE-001 |
| DT-07 | AI incompleta | Média | EPIC-AI-001 |
| DT-09 | Observabilidade runtime | Média | EPIC-OBS-001 |

---

## Mapeamento Backlog → Roadmap

| Epic | Release |
|------|---------|
| EPIC-GOV-001 | R1 |
| EPIC-CORE-001, EPIC-CORE-002 | R1 |
| EPIC-CORE-003, EPIC-HEX-001, EPIC-FE-001 | R2 |
| EPIC-SCH-001, EPIC-RES-001, EPIC-AI-001, EPIC-OBS-001 | R3 |
| EPIC-PLG-001, EPIC-MKT-001, EPIC-MOB-001 | R4 |

---

*Atualizar após cada sprint CF e aprovação de RFC.*
