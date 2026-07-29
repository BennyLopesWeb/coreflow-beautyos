# Relatório de Progresso — Assunção Técnica CoreFlow / BeautyOS

**Data:** 2026-07-28  
**Público:** liderança técnica, Product Owner, gestão  
**Branch:** `main`  
**HEAD local:** `b632ea8708ea860d1c0706b87b61a1b0750bfc29`  
**Remote:** `origin/main` em `e90df9e` — **local ahead 1** (commit B-TZ ainda sem push)

---

## 1. Resumo executivo

Neste ciclo de assunção técnica foi feito o seguinte:

1. **Diagnóstico completo** do repositório (relatório inicial + validação FASE 1–2).
2. **Validação de execução local** (FASE 3): ambiente Python 3.11, 485 testes verdes, fitness F5, API health e fluxo mínimo auth/booking.
3. **Correção prioritária (B-TZ)** do bug de timezone no `POST /v1/bookings`, com testes de regressão e **commit local**.

**Status geral do projeto:** permanece **Amarelo** — núcleo técnico saudável localmente; produção/homologação da API e hardening de segurança ainda não comprovados/resolvidos.

---

## 2. O que foi feito (com evidências)

### 2.1 Merge e baseline de código

| Entrega | Evidência |
|---------|-----------|
| Merge PR #26 (flatten payments read P8) | Commit `e90df9e` — *Merge pull request #26* |
| Release em código | `APP_VERSION = 2.20.0-r4-f17` em `backend/app/core/config.py` |
| Wave 1–2 Migration Ledger CRUD | `docs/architecture/MigrationLedger.md` — payments (read) P8 **DONE** |

### 2.2 Relatório de assunção inicial

| Entrega | Evidência |
|---------|-----------|
| Relatório completo de transição | `relatório.md` (raiz, ainda untracked) |
| Estrutura §§1–33 + resumo para 1ª reunião | mesmo arquivo |

### 2.3 Processo Prompt001 — FASE 1 a 3

| Fase | Entrega | Evidência |
|------|---------|-----------|
| FASE 1 | Baseline do estado do repo | `docs/assumption/baseline-technical-state.md` |
| FASE 2 | Validação N-01…N-10 (nebulosos) | `docs/assumption/fase2-nebulous-validation.md` |
| FASE 2/4 | Relatório de assunção e continuidade | `docs/assumption/relatorio-assuncao-continuidade.md` |
| FASE 3 | Execução local documentada | `docs/assumption/fase3-local-execution.md` |

### 2.4 Execução local validada (FASE 3)

| Validação | Resultado | Evidência |
|-----------|-----------|-----------|
| Ambiente | Python **3.11.13** + venv `backend/.venv` | FASE 3 doc |
| Dependências | `pip install -r requirements.txt` + `pytest-cov` | FASE 3 doc |
| Migração local | `make migrate` OK — tenant `salao-demo` | FASE 3 doc |
| Testes | **485 passed** (~167s) | `make test` |
| Architecture fitness | **PASS (F5)** | `make fitness` |
| Health | `GET /health` → 200 | smoke API |
| Platform | `GET /v1/platform/health` → `2.20.0-r4-f17` | smoke API |
| Auth | register/login/me OK | smoke API |
| Booking | create + get + cancel OK (naive datetime) | smoke API |
| Bug encontrado | ISO com `Z` → 400 timezone | FASE 3 doc |

### 2.5 Correção B-TZ (timezone) — commitada

| Item | Evidência |
|------|-----------|
| **Commit** | `b632ea8` — `fix(booking): normaliza scheduled_at timezone-aware no create` |
| **Autor** | Benigno Lopes \<benignofernandeslopes@gmail.com\> |
| Helper | `backend/app/shared/kernel/datetimes.py` (`as_naive_utc`) |
| Domain | `booking_domain_service.py` — normaliza `scheduled_at` no create |
| Legado | `disponibilidade_service.py` — normaliza data de entrada |
| Regressão | `test_r2_f1_booking_create.py` — `test_create_booking_accepts_scheduled_at_with_z` |
| Gate pré-commit | **10 passed** no arquivo + **fitness F5 PASS** |

### 2.6 Achados confirmados na validação (não inventados)

| Achado | Status | Evidência |
|--------|--------|-----------|
| Deploy da API no repo | **Não identificado** | TF `prod` só módulo CDN |
| Staging/prod API reais | **Necessita validação externa** | FE cita `https://api.trancapro.com` |
| `SECRET_KEY` / CORS defaults inseguros | **Confirmado** | `backend/app/core/config.py` |
| Payments write vs policy hexagonal | **Contradito pelo código** | write em `app/services/*` |
| FE misto `/v1` + legado | **Confirmado** | `filaService`, `pagamentoService`, etc. |
| Tag Git defasada | **Confirmado** | só `v1.20.1-r2-f2b` vs APP `2.20.0` |

---

## 3. O que ainda precisa ser feito

### 3.1 Imediato (operacional / Git)

| # | Ação | Prioridade | Dependência |
|---|------|------------|-------------|
| 1 | **Push** do commit `b632ea8` (ou abrir PR) | Alta | Autorização |
| 2 | Versionar `docs/assumption/*` (+ opcional `relatório.md`) | Alta | Decisão de o que entra no repo |
| 3 | Limpar/decidir untracked: prompts, comprovantes JPG, diffs em `terraform.tfvars.json` / evidence | Média | Revisão manual |
| 4 | Stakeholders: URL prod, staging, AWS keys, PO | Urgente | Pessoas |

### 3.2 Hardening e segurança (Sprint 1 sugerida)

| # | Item | Prioridade | Nota |
|---|------|------------|------|
| 5 | `SECRET_KEY` obrigatório fora de local | P0 | Aprovar via Prompt002 |
| 6 | Restringir `CORS_ORIGINS` | P0 | Idem |
| 7 | Confirmar remoção de access keys AWS estáticas | P0 | Só OIDC |
| 8 | Runbook backup/restore DB | P1 | Não existe no repo |

### 3.3 Produto / frontend

| # | Item | Prioridade | Nota |
|---|------|------------|------|
| 9 | Remover/migrar calls FE a rotas 410 (`/pagamentos/sinal*`, update/delete agenda legado) | P0 | Risco operacional |
| 10 | Alinhar fila legado → path core onde possível | P1 | Antes de `CORE_ENFORCEMENT_MODE=block` |
| 11 | Smoke E2E FE (typecheck/build) | P1 | Não executado na FASE 3 |
| 12 | Documentar `Idempotency-Key` obrigatório no create booking | P2 | DX |

### 3.4 Arquitetura e plataforma

| # | Item | Prioridade | Nota |
|---|------|------------|------|
| 13 | Definir **hospedagem/deploy da API** | P0 bloqueador go-live | Não está no Terraform atual |
| 14 | ADR: payments write (legado bridge vs hexagonal) | P1 | Alinhar policy × código |
| 15 | Tag Git = `2.20.0-r4-f17` (ou próximo release) | P2 | Versionamento |
| 16 | Atualizar `docs/00-EXECUTIVE-SUMMARY` | P2 | Desatualizado |
| 17 | Wave 3 OPS (platform/observability/ai/mobile) | P3 | **Só se PO priorizar** — não automático |
| 18 | `pytest-cov` em `requirements.txt` ou alinhar `pytest.ini` | P2 | CI já usa `-o addopts=""` |

### 3.5 Documentação FASE 8 ainda não gerada

Conforme Prompt001, após confirmação:

- `docs/assumption/project-current-state.md`
- `docs/assumption/unknowns-and-decisions.md`
- `docs/assumption/operational-readiness.md`
- `docs/assumption/decision-log.md`

---

## 4. Matriz “feito × pendente” (visão rápida)

| Tema | Feito | Pendente |
|------|-------|----------|
| Entendimento do repo | Sim (relatórios) | Ratificar com stakeholders |
| CI / testes locais | 485 + fitness | MySQL local opcional; FE tests |
| Bug timezone booking | Sim + commit | Push |
| Segurança defaults | Identificado | Hardening código |
| Deploy API | Diagnosticado como ausente | Decisão + implementação |
| Ambientes reais | Não comprovados | Validação externa |
| FE legado | Mapeado | Correção de rotas |
| Wave 3 flatten | — | Backlog técnico sob PO |
| Docs assumption no Git | Locais untracked | Commit/PR docs |

---

## 5. Riscos que permanecem abertos

1. **Crítico (go-live):** sem deploy da API auditável no repositório.  
2. **Crítico (se prod usar defaults):** `SECRET_KEY` / CORS `*`.  
3. **Alto:** FE ainda chama caminhos legado/410.  
4. **Alto:** bus factor (histórico concentrado em um autor).  
5. **Médio:** docs executivos e tag Git desalinhados da release `2.20.0`.

---

## 6. Recomendações para a próxima reunião (15 min)

1. Autorizar **push/PR** de `b632ea8`.  
2. Autorizar commit dos **docs de assunção**.  
3. Responder: existe staging/prod da API? Quem opera `api.trancapro.com`?  
4. Aprovar IDs no Prompt002 para **hardening** (SECRET/CORS) e/ou **FE 410**.  
5. Explicitar prioridade: operação BeautyOS vs Wave 3 CoreFlow.

---

## 7. Anexos — índice de documentos

| Documento | Conteúdo |
|-----------|----------|
| `relatório.md` | Assunção técnica completa (diagnóstico inicial) |
| `docs/assumption/baseline-technical-state.md` | Snapshot FASE 1 |
| `docs/assumption/fase2-nebulous-validation.md` | Tabela N-01…N-10 |
| `docs/assumption/relatorio-assuncao-continuidade.md` | Continuidade / backlog / sprints |
| `docs/assumption/fase3-local-execution.md` | Resultados FASE 3 + nota B-TZ |
| `docs/assumption/relatorio-progresso-apresentacao.md` | **Este documento** |
| Commit `b632ea8` | Fix timezone booking |
| Commit `e90df9e` | Merge P8 payments flatten (base remota) |

---

## 8. Conclusão

O projeto foi **assumido com método**: estado preservado, hipóteses do relatório anterior validadas ou contestadas com evidência, execução local comprovada e o principal bug bloqueante do smoke (**timezone no create booking**) já corrigido e commitado.

O caminho seguro agora é **publicar o fix**, **persistir a documentação de assunção no Git**, e só então atacar **segurança + FE legado + decisão de deploy** — sem saltar para Wave 3 sem prioridade de negócio.
