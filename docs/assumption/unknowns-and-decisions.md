# Questões nebulosas e decisões — Assunção técnica

**Referência de código:** `b632ea8`  
**Data:** 2026-07-28  

Status permitidos: Aberta · Em investigação · Decidida · Bloqueada · Cancelada

---

## Questões nebulosas

| ID | Questão | Evidência | Status | Responsável sugerido | Prazo | Impacto |
|----|---------|-----------|--------|----------------------|-------|---------|
| U-01 | API de produção existe e responde em `https://api.trancapro.com`? | Hostname no FE (`frontend/src/config/api.ts`); sem prova de uptime | Aberta | Ops / stakeholder | Urgente | Go-live |
| U-02 | Existe staging da API (URL, DB, owners)? | TF staging = CDN; D6 simulada | Aberta | Ops | Urgente | Homologação |
| U-03 | Onde e como a API é hospedada/deployada? | Dockerfile local; TF prod só `coreflow_cdn` | Aberta | Arch / Ops | Urgente | Publicação |
| U-04 | Estratégia de backup/restore/RTO/RPO do banco | Ausente em `docs/ops` (só OIDC) | Aberta | Ops / DBA | Alta | Dados |
| U-05 | Access keys AWS estáticas já foram removidas (só OIDC)? | Runbook OIDC recomenda remoção | Aberta | Ops / segurança | Alta | Segurança |
| U-06 | Prioridade PO: BeautyOS operação vs Wave 3 CoreFlow? | Ledger Wave 3 TODO; Prompt002 proíbe Wave 3 sem PO | Aberta | Product Owner | Alta | Roadmap |
| U-07 | Quorum de aprovação de merge/ADR além do autor único? | Histórico Git concentrado | Aberta | Governança | Média | Processo |
| U-08 | Provedor PIX/gateway real em uso? | `PaymentProviderPort` + mocks/flags | Em investigação | Backend | Média | Pagamentos |
| U-09 | Quais rotas FE legado ainda quebram em runtime (410)? | Código FE mapeado; E2E não rodado | Em investigação | Frontend | Alta | UX |
| U-10 | `terraform.tfvars.json` (dev) — alteração local intencional? | Working tree modified; keys CDN only | Em investigação | Quem alterou | Baixa | Drift local |

---

## Decisões (somente aprovadas ou explicitamente em aberto)

| ID | Decisão | Contexto | Alternativas | Status | Decisor | Impacto |
|----|---------|----------|--------------|--------|---------|---------|
| D-01 | Não iniciar Wave 3 sem priorização PO | Prompt002 / assunção | Iniciar Wave 3 agora | Decidida (processo) | Liderança técnica + Prompt002 | Escopo |
| D-02 | Não mover payments write para hexagonal nesta fase | Prompt002 | Refactor payments agora | Decidida (processo) | Prompt002 | Escopo |
| D-03 | Normalizar `scheduled_at` aware → naive UTC no create | Bug FASE 3 | Rejeitar Z / migrar tudo aware | Decidida (código `b632ea8`) | Assunção + commit | Booking |
| D-04 | Publicar `b632ea8` via PR controlado (sem push automático) | Continuidade | Push direto em main | Aberta (aguardando OK push) | Usuário | Release |
| D-05 | Versionar pacote `docs/assumption/*` (docs oficiais) | Prompt documentação | Manter só local | Aberta (docs criados; commit pendente) | Usuário | Conhecimento |
| D-06 | Hardening SECRET_KEY/CORS | Risco FASE 2 | Adiar | Aberta | Aprovar via Prompt002 IDs | Segurança |
| D-07 | Alvo de hospedagem da API | Deploy não no repo | VM / ECS / K8s / PaaS | Aberta | Arch + PO | Infra |

**Regra:** hipóteses não aparecem como “Decidida”. Inferências ficam em U-* ou status Aberta.
