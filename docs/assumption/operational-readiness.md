# Prontidão operacional — Assunção técnica

**Referência de código:** `b632ea8`  
**Data:** 2026-07-28  

Legenda: **Comprovado** · **Parcial** · **Não comprovado** · **Não identificado no repositório**

---

## Pré-requisitos locais

| Item | Estado | Como |
|------|--------|------|
| Python 3.11 | Comprovado | `python3.11 -m venv backend/.venv` |
| Dependências | Comprovado | `pip install -r backend/requirements.txt` (+ `pytest-cov` se usar addopts do `pytest.ini`) |
| Variáveis | Parcial | Copiar `backend/.env.example` → `backend/.env` (não versionar) |
| Docker (opcional) | Disponível na máquina de assunção | `make docker-mysql-up` etc. |

---

## Como executar localmente

```bash
cd backend && source .venv/bin/activate   # ou criar venv 3.11
pip install -r requirements.txt
cp -n .env.example .env
cd .. && make migrate
make run          # API :8000
# outro terminal:
curl -s http://127.0.0.1:8000/health
```

**Comprovado** na FASE 3.

---

## Como testar

```bash
source backend/.venv/bin/activate
make test         # pytest -o addopts="" → 485 passed (FASE 3)
make fitness      # F5 PASS
# regressão timezone:
cd backend && python -m pytest tests/test_core/test_r2_f1_booking_create.py -q -o addopts=""
```

**Comprovado** (FASE 3 + pós-`b632ea8`).

MySQL: job CI `test-mysql` — **Parcial** (não reexecutado localmente nesta assunção).

---

## Como publicar (estado atual)

| Caminho | Estado |
|---------|--------|
| Push commit `b632ea8` / PR | Preparado — **aguardando autorização de push** |
| CI GitHub (test, test-mysql, fitness) | Existe em `.github/workflows/` — **Parcial** (não reexecutado neste ambiente após o commit) |
| Deploy API cloud | **Não identificado no repositório** |
| CDN / Terraform | Workflows + envs `dev/staging/prod` (módulo CDN) — **Parcial** (edge, não API) |
| Mobile EAS | Workflow `mobile-eas.yml` — **Não comprovado** nesta assunção |

### Comando sugerido para publicar o fix (NÃO executar sem OK)

Ver seção FASE C / Prompt de comandos — tipicamente:

```bash
git push -u origin HEAD
# ou branch dedicada + gh pr create
```

---

## Como fazer rollback

| Escopo | Procedimento | Estado |
|--------|--------------|--------|
| Commit `b632ea8` ainda não no remote | Não publicar / `git revert` local se necessário | Comprovado (git) |
| Após merge no remote | `git revert b632ea8` + PR | Inferência padrão Git |
| Deploy API | **Não identificado** | — |
| CDN Terraform | Plan/apply reverso via workflows — **Parcial** | docs/ops OIDC |

---

## Como verificar saúde

| Check | Endpoint / comando | Estado |
|-------|-------------------|--------|
| Liveness simples | `GET /health` | Comprovado |
| Platform | `GET /v1/platform/health` | Comprovado |
| Versão | campo `version` no platform health | Comprovado |

---

## Banco de dados

| Item | Estado |
|------|--------|
| Dev SQLite | Comprovado (`make migrate`) |
| CI MySQL 8 | Comprovado no workflow |
| Staging/prod DB | **Não comprovado** |
| Backup automatizado | **Não identificado no repositório** |
| Restore documentado | **Não identificado no repositório** |
| Migração destrutiva histórica | Fato: DROP `agendamentos` (`cf016`) — não reexecutar sem aprovação |

---

## Segurança operacional

| Item | Estado |
|------|--------|
| JWT local | Comprovado |
| Defaults `SECRET_KEY` / CORS | **Risco confirmado** — endurecer antes de não-dev |
| Secrets neste documento | Nenhum valor incluído |
| Rate limiting | **Não identificado** |

---

## Critérios de produção (checklist)

- [ ] Ambiente prod API identificado e acessível  
- [ ] `SECRET_KEY` forte via secret store (não default)  
- [ ] CORS restrito  
- [ ] Deploy + rollback da API documentados e testados  
- [ ] Backup/restore ensaiados  
- [ ] FE sem calls críticas a rotas 410  
- [ ] CI verde no commit a promover  
- [ ] Observabilidade mínima (logs/alertas) comprovada  

**Veredito atual:** **não pronto para produção** com base apenas no repositório e na assunção local.
