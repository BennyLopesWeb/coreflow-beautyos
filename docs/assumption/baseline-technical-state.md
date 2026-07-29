# Baseline — Estado técnico (FASE 1)

**Data e horário da análise:** 2026-07-28 22:01:36 -03  
**Analista:** liderança técnica (assunção via Prompt001)  
**Fonte de processo:** `Prompt001.md` §3

---

## Identidade do snapshot

| Campo | Valor |
|-------|--------|
| Diretório | `/Users/zeuser/Documents/ProjetosPessoas/Atendente Salao trancista` |
| Branch | `main` (tracking `origin/main`) |
| Commit | `e90df9ef6244d5c9dd042467bd62b163719de38e` |
| Mensagem HEAD | Merge pull request #26 from BennyLopesWeb/r2-payments-read-flatten-p8 |
| Ahead/behind | `0 / 0` (alinhado com `origin/main`) |
| Remote | `https://github.com/BennyLopesWeb/coreflow-beautyos.git` |
| Tag Git | `v1.20.1-r2-f2b` (única; **não** alinhada a APP_VERSION) |
| Versão aplicação | `2.20.0-r4-f17` (`backend/app/core/config.py`) |

---

## Status da árvore de trabalho

| Estado | Detalhe |
|--------|---------|
| Tracked modified | Nenhum |
| Staged | Nenhum |
| Untracked (no momento do baseline) | `Prompt001.md`, `Prompt002-Autorizar continuidade`, `Prompt-para-aprovação-do-commit.md`, `relatório.md` |
| `docs/assumption/` | Criado nesta assunção |

**Observação:** Os untracked são artefatos de processo/documentação local da assunção; **não** fazem parte do commit `e90df9e`.

---

## Ambiente local observado

| Item | Valor | Nota |
|------|--------|------|
| Python | 3.10.13 (pyenv) | CI usa **3.11** — divergência |
| Node / npm | v22.13.1 / 10.9.2 | — |
| venv dedicado | Não encontrado | — |
| `.env` backend | Só `backend/.env.example` | Sem `.env` local |
| Docker | 29.2.1 | Compose v5.1.0 |
| Cliente `mysql` CLI | Não no PATH | MySQL via Docker possível |
| Dependências pip projeto | Não inventariadas nesta fase | FASE 3 |

---

## Estrutura principal relevante

- `backend/` — FastAPI, Alembic, tests, plugins
- `frontend/` — Expo (`beautyos-mobile`)
- `docs/` — SAB, sprints, releases, architecture
- `infra/terraform/` — CDN (+ `ci-oidc`); envs `dev`/`staging`/`prod`
- `.github/workflows/` — CI, fitness, CDN, Terraform, EAS
- `scripts/` — ops, migration lint, fitness
- `packages/coreflow-sdk/`
- `Makefile`, `docker-compose*.yml`

### Arquivos de configuração relevantes

- `Makefile`
- `backend/requirements.txt`
- `backend/pytest.ini` (addopts inclui `--cov*` — ver limitações)
- `backend/.env.example`
- `backend/app/core/config.py`
- `docker-compose.yml` (+ overlays mysql/kafka/rabbitmq/cdn)
- `frontend/package.json`, `frontend/eas.json`, `frontend/src/config/api.ts`
- `.github/workflows/ci.yml` e demais workflows

---

## Limitações da análise (baseline)

- Sem acesso a staging/produção remotos.
- Sem execução da API ou suite completa de testes neste arquivo.
- Secrets não lidos/expostos.
- `relatório.md` anterior tratado como **hipótese**, não verdade.

---

## Observações iniciais

1. HEAD confirma o commit de referência do relatório de assunção.
2. Release de código `2.20.0-r4-f17` vs tag Git `v1.20.1-r2-f2b`.
3. Python local ≠ CI — risco para FASE 3.
4. Terraform `prod`/`staging` existem, mas (validação FASE 2) cobrem módulo CDN, não API.
5. Frontend não-dev aponta para `https://api.trancapro.com` — hostname pretendido; liveness **não** comprovada aqui.

---

## Próximo passo (após este baseline)

FASE 2 — validação dos pontos nebulosos N-01…N-10 → ver `docs/assumption/fase2-nebulous-validation.md` e `docs/assumption/relatorio-assuncao-continuidade.md`.
