# CoreFlow Platform — Índice da Documentação (SAB)

**Software Architecture Blueprint** · **Build Once. Configure Everywhere.**

## Governança arquitetural (novo — jul/2026)

| Documento | Descrição |
|-----------|-----------|
| [**ArchitectureAssessment.md**](./ArchitectureAssessment.md) | Auditoria completa do estado atual |
| [**CONSTITUTION.md**](./CONSTITUTION.md) | **Constituição imutável da plataforma** |
| [**ArchitecturePrinciples.md**](./ArchitecturePrinciples.md) | 15 princípios derivados da Constituição |
| [**ReleaseGovernance.md**](./ReleaseGovernance.md) | Fluxo oficial RFC → ADR → Sprint → PR |
| [**decisions/DefinitionOfReady-Architecture.md**](./decisions/DefinitionOfReady-Architecture.md) | DoR — gate antes de cada fase |
| [**decisions/DefinitionOfDone-Architecture.md**](./decisions/DefinitionOfDone-Architecture.md) | DoD — gate após cada fase |
| [**decisions/ADR-Lifecycle.md**](./decisions/ADR-Lifecycle.md) | Imutabilidade e estados dos ADRs |
| [**ArchitectureDecisionLog.md**](./ArchitectureDecisionLog.md) | Changelog cronológico de decisões |
| [**DomainOwnership.md**](./DomainOwnership.md) | Ownership por bounded context |
| [**reviews/ArchitectureCompliance.md**](./reviews/ArchitectureCompliance.md) | Health check arquitetural por release |
| [**CoreMetaModel.md**](./CoreMetaModel.md) | Meta modelo universal |
| [**ArchitectureDecisionIndex.md**](./ArchitectureDecisionIndex.md) | Índice ADR/RFC |
| [**ArchitectureEvolutionPlan.md**](./ArchitectureEvolutionPlan.md) | Plano de evolução incremental |
| [**ArchitectureVision2030.md**](./ArchitectureVision2030.md) | Visão 5 anos |
| [**Backlog.md**](./Backlog.md) | Backlog MoSCoW (Epic/Feature/Story) |
| [**roadmap/Roadmap-12M.md**](./roadmap/Roadmap-12M.md) | Releases jul/2026 – jun/2027 |
| [**rfc/**](./rfc/) | Request for Comments (propostas) |
| [**adr/**](./adr/) | Architecture Decision Records |
| [**decisions/PR-Checklist.md**](./decisions/PR-Checklist.md) | Checklist obrigatório de PR |
| [**architecture/**](./architecture/) | Arquitetura alvo, Event Catalog |

**Regra:** implementação de código significativa **bloqueada** até RFC + ADR aprovados.

## Documentação estratégica (pós Foundation — jul/2026)

| Documento | Descrição |
|-----------|-----------|
| [**PlatformVision.md**](./PlatformVision.md) | Missão, visão 5 anos, personas, competitivo |
| [**BoundedContexts.md**](./BoundedContexts.md) | Mapa DDD de contextos delimitados |
| [**CoreVsPlugins.md**](./CoreVsPlugins.md) | Critérios Core vs Plugin + matriz |
| [**ProductCapabilityMap.md**](./ProductCapabilityMap.md) | Inventário de capacidades |
| [**DeveloperPortal.md**](./DeveloperPortal.md) | Guia extensão da plataforma |
| [**EngineeringHandbook.md**](./EngineeringHandbook.md) | Padrões de engenharia |
| [**PlatformRoadmap2030.md**](./PlatformRoadmap2030.md) | Releases R2–R7 até 2031 |
| [**EcosystemStrategy.md**](./EcosystemStrategy.md) | Marketplace, SDK, ecossistema |
| [**ArchitectureMetrics.md**](./ArchitectureMetrics.md) | KPIs arquiteturais contínuos |
| [**templates/SprintTemplate.md**](./templates/SprintTemplate.md) | Template oficial de sprint (R2–R6) |
| [**sprints/R2-F1.md**](./sprints/R2-F1.md) | Sprint R2-F1 — ✅ Accepted (tech) |
| [**sprints/R2-F1b.md**](./sprints/R2-F1b.md) | Sprint R2-F1b — ✅ Accepted (tech) |
| [**reviews/R2-F1b-GateReview.md**](./reviews/R2-F1b-GateReview.md) | Gate Review F1b — ✅ ACCEPTED |
| [**sprints/R2-F2.md**](./sprints/R2-F2.md) | Sprint R2-F2 — ⏳ Ready (DoR) |
| [**checklists/R2-F1-StagingValidation.md**](./checklists/R2-F1-StagingValidation.md) | Checklist staging F1 |

## Platform Strategy v3 — 20 pilares (pré-R2)

**Índice mestre:** [**PlatformStrategyIndex.md**](./PlatformStrategyIndex.md)

| # | Documento | Tema |
|---|-----------|------|
| 1 | [DomainRegistry.md](./DomainRegistry.md) | Catálogo único de domínios |
| 2 | [EventStorming.md](./EventStorming.md) | Fluxos causais oficiais |
| 3 | [EventDrivenArchitecture.md](./EventDrivenArchitecture.md) | Envelope, Kafka, transport |
| 4 | [APIVersioning.md](./APIVersioning.md) | v1 stable, sunset, migration |
| 5 | [APIGovernance.md](./APIGovernance.md) | Naming, errors, pagination |
| 6–7 | [MobilePlatform.md](./MobilePlatform.md) | BFF, SDK-first, offline |
| 8 | [RealtimePlatform.md](./RealtimePlatform.md) | WebSocket, SSE, live updates |
| 9 | [SearchEngine.md](./SearchEngine.md) | Global search cross-entity |
| 10 | [AIArchitecture.md](./AIArchitecture.md) | LLM Gateway, RAG, audit |
| 11 | [ObservabilityPlatform.md](./ObservabilityPlatform.md) | Logs, traces, business metrics |
| 12 | [FeatureFlagPlatform.md](./FeatureFlagPlatform.md) | Targeting, kill switch |
| 13 | [MarketplaceEconomy.md](./MarketplaceEconomy.md) | Revenue share, trials |
| 14 | [ResourceEngine.md](./ResourceEngine.md) | Core universal por vertical |
| 15 | [DomainTemplates.md](./DomainTemplates.md) | Beauty/Sports/Clinic starters |
| 16 | [PlatformBilling.md](./PlatformBilling.md) | SaaS billing CoreFlow |
| 17 | [DigitalTwin.md](./DigitalTwin.md) | Gêmeo digital tenant |
| 18 | [DigitalOperationsCenter.md](./DigitalOperationsCenter.md) | Centro de comando |
| 19 | [CapabilityMaturityDashboard.md](./CapabilityMaturityDashboard.md) | Maturidade por capability |
| 20 | [AgenticAIArchitecture.md](./AgenticAIArchitecture.md) | Agent runtime, HITL |

## Ecossistema & Business Platform (v2)

| Documento | Descrição |
|-----------|-----------|
| [**BusinessCapabilities.md**](./BusinessCapabilities.md) | Business Capability Model (26 capabilities) |
| [**IntegrationHub.md**](./IntegrationHub.md) | Hub de integrações event-driven |
| [**TenantCustomizationEngine.md**](./TenantCustomizationEngine.md) | Personalização no-code por tenant |
| [**LowCodePlatform.md**](./LowCodePlatform.md) | Plataforma visual workflows/forms/BI |
| [**BusinessRulesEngine.md**](./BusinessRulesEngine.md) | Motor declarativo de regras |
| [**APIMarketplace.md**](./APIMarketplace.md) | Marketplace de ativos + monetização |
| [**BusinessIntelligence.md**](./BusinessIntelligence.md) | BI, previsões, arquitetura de dados |
| [**DeveloperExperience.md**](./DeveloperExperience.md) | CLI `coreflow`, DX, produtividade |
| [**PluginCertification.md**](./PluginCertification.md) | Pipeline certificação marketplace |
| [**ArchitectureFitnessFunctions.md**](./ArchitectureFitnessFunctions.md) | Testes arquiteturais CI |
| [**PlatformMaturityModel.md**](./PlatformMaturityModel.md) | 6 níveis de maturidade |
| [**EcosystemStrategy.md**](./EcosystemStrategy.md) | Estratégia ecossistema v2 |
| [**R2-ExecutionPlan.md**](./R2-ExecutionPlan.md) | Plano Release 2 v2 ⏳ aguarda aprovação |

## Estrutura final (00–20)

| # | Capítulo | Pasta | Status |
|---|----------|-------|--------|
| 00 | Executive Summary | `00-EXECUTIVE-SUMMARY/` | 🔜 |
| 01 | Vision | `00-VISION/` → renumerar | ⚠️ |
| 02 | Business Model | `02-BUSINESS-MODEL/` | 🔜 |
| 03 | Market Position | `03-MARKET-POSITION/` | 🔜 |
| 04 | Architecture | `01-ARCHITECTURE/` → renumerar | ⚠️ |
| 05 | Domain Model | `05-DOMAIN-MODEL/` | 🔜 |
| 06 | Plugin Framework | `03-PLUGINS/` → expandir | ⚠️ |
| 07 | **Meta Model** | `07-META-MODEL/` | ⚠️ **coração** |
| 08 | AI Platform | `08-AI-PLATFORM/` | 🔜 |
| 09 | Scheduling Engine | `09-SCHEDULING-ENGINE/` | 🔜 |
| 10 | Marketplace | `10-MARKETPLACE/` | 🔜 |
| 11 | Mobile Strategy | `11-MOBILE-STRATEGY/` | 🔜 |
| 12 | Event Driven | `12-EVENT-DRIVEN/` | 🔜 |
| 13 | Security | `13-SECURITY/` | 🔜 |
| 14 | Multi Tenant | `14-MULTI-TENANT/` | 🔜 |
| 15 | SDK | `15-SDK/` | 🔜 |
| 16 | Roadmap | `16-ROADMAP/` | 🔜 |
| 17 | Sprints | `04-SPRINTS/` → renumerar | ⚠️ CF-0..3 ✅ |
| 18 | Cursor Prompts | `18-CURSOR-PROMPTS/` | 🔜 |
| 19 | ADR | `06-ADR/` → renumerar | ⚠️ |
| 20 | Future Vision | `20-FUTURE-VISION/` | 🔜 |

Legenda: ✅ completo · ⚠️ parcial · 🔜 planejado

## Documentos-chave existentes

| Documento | Conteúdo |
|-----------|----------|
| [`COREFLOW_GAP_ANALYSIS.md`](./COREFLOW_GAP_ANALYSIS.md) | **Análise gap vs visão final** |
| [`07-META-MODEL/README.md`](./07-META-MODEL/README.md) | Meta Model — coração da plataforma |
| [`00-VISION/Vision.md`](./00-VISION/Vision.md) | Visão e princípios |
| [`04-SPRINTS/Sprint00–03.md`](./04-SPRINTS/Sprint00.md) | Entregas CF-0 a CF-3 |
| [`06-ADR/ADR001-metamodel.md`](./06-ADR/ADR001-metamodel.md) | ADR metamodelo |
| [`../DOCUMENTACAO.md`](../DOCUMENTACAO.md) | Regras de negócio Beauty (plugin piloto) |
| [`../COREFLOW_ANALYSIS.md`](../COREFLOW_ANALYSIS.md) | Análise estratégica (atualizar) |

## Código vs documentação

| Sprint | Foco | Versão |
|--------|------|--------|
| CF-0 | Plugin Loader, identity, events | 0.1.0 |
| CF-1 | Catalog/Offering/Booking + CQRS | 0.1.0 |
| CF-2 | Location/Worker/Resource + Alembic | 0.2.0 |
| CF-3 | MySQL Docker + frontend v1 + Sunset | 0.3.0 |
| CF-4 | Scheduling/Resource Engine | 0.4.0 |
| CF-5 | core_customers + Outbox + booking v1 | 0.5.0 |
| CF-6 | core_payments + OTEL + CI MySQL | 0.6.0 |
| CF-7 | core_waitlist + BeautyAgent + SDK | 0.7.0 |
| CF-8 | Workflow + AI LLM + Enforcement | 0.8.0 |
| CF-9 | Order/Invoice + Workflow editor | 0.9.0 |
| CF-10 | Asset/Inventory + Marketplace | 1.0.0 |
| CF-11 | Mobile SDK + plugins verticais + production warn | 1.1.0 |
| CF-12 | Deep links + push outbox + production block | 1.2.0 |
| CF-13 | Expo Push + universal links + RabbitMQ worker | 1.3.0 |
| CF-14 | Well-known + Expo Notifications + Kafka | 1.4.0 |
| CF-15 | CDN well-known + EAS + Schema Registry | 1.5.0 |
| CF-16 | Confluent SR + CDN multi-plugin + EAS CI | 1.6.0 |
| CF-17 | EAS white-label + Avro completo + CDN S3 | 1.7.0 |
| CF-18 | EAS Submit + Avro evolution + CloudFront | 1.8.0 |
| CF-19 | EAS Update OTA + Kafka DLQ + Terraform CDN | 1.9.0 |
| CF-20 | DLQ replay + EAS rollout + Terraform CI | 1.10.0 |
| CF-21 | DLQ handler replay + EAS canary + Terraform pipeline | 1.11.0 |
| CF-22 | Prometheus DLQ + canary auto-promote + Terraform drift | 1.12.0 |
| CF-23 | Grafana dashboards + canary rollback + Terraform OPA | 1.13.0 |
| CF-24 | Alertmanager + rollback worker + Terraform Sentinel | 1.14.0 |
| CF-25 | PagerDuty/Opsgenie + canary DB persist + TFC | 1.15.0 |

## Pastas de domínio (governança)

| Pasta | Conteúdo |
|-------|----------|
| `architecture/` | Target architecture, Event Catalog |
| `core/` | Core Framework modules |
| `plugins/` | Plugin framework |
| `ai/` | AI Platform |
| `workflow/` | Workflow Engine |
| `sdk/` | SDKs |
| `resource-engine/` | Resource Engine |
| `scheduling-engine/` | Scheduling Engine |
| `sprints/` | → `04-SPRINTS/` |

## Autor

Benigno Fernandes Lopes
