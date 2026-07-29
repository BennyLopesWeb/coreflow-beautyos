# Relatório de Assunção e Continuidade

## 1. Estado do repositório

- **Branch:** `main` (`origin/main`)
- **Commit:** `e90df9ef6244d5c9dd042467bd62b163719de38e`
- **Status:** tracked limpo; untracked locais de processo (`Prompt001.md`, `Prompt002-*`, `Prompt-para-aprovação-do-commit.md`, `relatório.md`) + docs criados em `docs/assumption/`
- **Versão:** `2.20.0-r4-f17`
- **Data:** 2026-07-28
- **Limitações:** sem staging/prod remotos; suite pytest não executada (apenas collect); Python local 3.10 vs CI 3.11

Baseline: [`baseline-technical-state.md`](./baseline-technical-state.md)  
Detalhe N-*: [`fase2-nebulous-validation.md`](./fase2-nebulous-validation.md)

## 2. O que foi confirmado

- HEAD = commit de referência do relatório anterior.
- Stack: FastAPI + SQLAlchemy/Alembic + Expo; SQLite local / MySQL no CI.
- Release código `2.20.0-r4-f17`; Wave 1–2 Migration Ledger DONE (incl. payments read P8).
- CI: `test` + `test-mysql` + architecture fitness.
- Dockerfile + compose para API local.
- Terraform envs CDN (dev/staging/prod) + GitHub OIDC.
- JWT implementado; comprovante com validação MIME + 5MB.
- 485 testes coletáveis com override de addopts.
- FE usa `/v1/bookings` para ciclo principal e comprovante core.
- Defaults `SECRET_KEY` fraco e `CORS=*`.
- Payments **read** em módulo flat; **write** em `app/services`.

## 3. O que foi contradito

- Policy: payments write = hexagonal CORE → **código** mantém write em services legado (bridge), com docstring explícita no provider.
- Tag Git `v1.20.1-r2-f2b` ≠ APP_VERSION `2.20.0-r4-f17`.
- Pasta Terraform `prod` **não** prova API em produção (só CDN).
- Executive summary antigo (CF-4 / 50+ testes) vs realidade (R4 + 485 casos) — já apontado no `relatório.md`.

## 4. O que permanece nebuloso

- API em produção/homologação reais (uptime, DB, owners).
- Deploy/rollback da API.
- Backup/RTO/RPO.
- Provedor PIX/gateway real em uso.
- Rotação efetiva de keys AWS estáticas.
- Prioridade de negócio Wave 3 vs operação BeautyOS.
- Compilação FE e fluxo E2E manual.

## 5. Ambiente local

| Item | Estado |
|------|--------|
| Python | 3.10.13 (≠ CI 3.11) |
| venv / `.env` | Ausentes |
| Docker | Disponível |
| API/testes runtime | Pendente FASE 3 |

## 6. Ambiente de homologação

API staging: **Não confirmado no repositório.**  
CDN staging as-code: parcial.  
D6: testes simulados locais.

## 7. Ambiente de produção

Hostname pretendido FE: `https://api.trancapro.com` — **Necessita validação externa.**  
CDN prod Terraform: presente.  
Operação API: **Necessita validação externa.**

## 8. Deploy da API

**Deploy da API não identificado no repositório.**  
Build: Docker local + CI testes. Mobile: EAS. Edge: CDN sync OIDC.

## 9. Banco de dados

SQLite (dev) / MySQL 8 (CI + compose). Alembic até `cf016` (DROP agendamentos).  
Backup operacional: **Não identificado no repositório.**

## 10. Segurança

| Item | Severidade |
|------|------------|
| SECRET_KEY default | Crítico (não-dev) |
| CORS `*` | Alto |
| Sem rate limit | Médio |
| Upload comprovante controlado | Mitigado |
| SCA deps | Não avaliado |

## 11. Pagamentos

Read core (`/v1/payments` + `PaymentService`).  
Write: `PaymentReservationService` / `ComprovanteService`.  
Provider: Protocol/mock path; webhook `/webhook/pix` existe.  
FE: comprovante core; ainda chama `/pagamentos/sinal*` em serviços.

## 12. Legado versus Core

Coexistência confirmada. FE depende de `/fila` e trechos agenda/pagamentos legado. Remoção sem matriz = alto risco.

## 13. Feature flags

Booking core ON; resource/AI/workflow/plugin OFF; enforcement `off`. Ativar enforcement `block` sem migrar FE legado pode quebrar operação.

## 14. Frontend

Expo + EAS; auth e booking v1 presentes; fila legado; sem testes app; URL prod hardcoded; typecheck/build **não** validados nesta fase.

## 15. Testes

485 coletados; 69 arquivos; CI usa `-o addopts=""`. Local sem override falha por `--cov` (pytest-cov provavelmente ausente). Execução pass/fail: pendente FASE 3.

## 16. Problemas encontrados

1. Deploy API ausente no repo.  
2. Defaults de segurança inseguros.  
3. Divergência policy vs payments write.  
4. FE misto v1/legado (risco 410).  
5. Python local ≠ CI; pytest.ini cov vs deps.  
6. Docs executivos desatualizados.  
7. Tag Git defasada.

## 17. Bloqueadores

| ID | Item | Notas |
|----|------|-------|
| BL-01 | Deploy/hospedagem API não definido no repo | Impede go-live auditável |
| BL-02 | Ambientes staging/prod API não comprovados | Impede promoção segura |
| BL-03 | (Local) falta validar `make test`/`make run` neste host | Impede desenvolvimento confiante até FASE 3 |

## 18. Riscos priorizados

| ID | Item | Categoria | Evidência | Impacto | Prioridade | Dependências |
|----|------|-----------|-----------|---------|------------|--------------|
| R-01 | SECRET_KEY/CORS defaults | Segurança | config.py | Crítico | P0 | Aprovação Sprint 1 |
| R-02 | Deploy API desconhecido | Publicação | TF só CDN | Crítico | P0 | Stakeholder |
| R-03 | FE legado vs 410 | Correção funcional | pagamentoService/agendamentoService | Alto | P0 | Mapa rotas |
| R-04 | Sem backup documentado | Perda de dados | ausência ops | Alto | P1 | Infra |
| R-05 | Enforcement block prematuro | Operação | flags + FE fila | Alto | P1 | Migração FE |
| R-06 | Bus factor 1 | Processo | git shortlog | Alto | P1 | Governança |
| R-07 | pytest-cov/ini drift | Capacidade testar | pytest.ini | Médio | P2 | FASE 3 |
| R-08 | Wave 3 sem prioridade negócio | Dívida | Ledger | Médio | P3 | PO |

## 19. Backlog recomendado

| ID | Item | Tipo | Prioridade |
|----|------|------|------------|
| B-01 | Validar URL `api.trancapro.com` e owners | Investigação | P0 |
| B-02 | Definir hospedagem API + runbook mínimo | Infra | P0 |
| B-03 | FASE 3: venv 3.11, `make test`, health | Execução local | P0 |
| B-04 | Hardening SECRET_KEY + CORS (não-dev) | Segurança | P0 |
| B-05 | Eliminar calls FE para rotas 410 | Bug/Feature | P0 |
| B-06 | ADR payments write vs policy | Decisão arch | P1 |
| B-07 | Runbook backup/restore | Docs ops | P1 |
| B-08 | Alinhar pytest.ini / pytest-cov | Teste | P2 |
| B-09 | Atualizar exec summary + tag Git | Docs | P2 |
| B-10 | Wave 3 OPS | Débito | P3 (só se PO ok) |

## 20. Sprint de estabilização

### Sprint 0 — Assunção e estabilização

- **Objetivo:** Baseline confiável + execução local + mapa ambientes/legado.
- **Escopo:** docs assumption; FASE 3 local; inventário FE 410; perguntas stakeholders.
- **Fora:** Wave 3 flatten; mover payments; remover legado em massa; deploy cloud sem desenho.
- **Aceite:** `make test` verde local (ou lista de falhas); health OK; matriz FE legado publicada.
- **Rollback:** N/A (docs/local).
- **Testes:** collect + suite Makefile.

### Sprint 1 — Hardening mínimo (após aprovação explícita de IDs)

SECRET_KEY obrigatório fora de local; CORS restrito; docs config; regressões.

## 21. Próxima funcionalidade recomendada

**Não** Wave 3 por padrão.  
Prioridade sugerida de **negócio operacional BeautyOS:** corrigir FE que ainda chama rotas sunset/410 (pagamentos sinal / agenda update-delete) e estabilizar fila→core — menor risco e desbloqueia enforcement futuro.  
**Confirmar com PO** antes de implementar.

## 22. Alterações realizadas

| Arquivo | Tipo |
|---------|------|
| `docs/assumption/baseline-technical-state.md` | Criado |
| `docs/assumption/fase2-nebulous-validation.md` | Criado |
| `docs/assumption/relatorio-assuncao-continuidade.md` | Criado |

Nenhuma alteração de código de aplicação.

## 23. Testes executados

| Validação | Resultado | Evidência | Observação |
|-----------|-----------|-----------|------------|
| pytest collect `-o addopts=""` | OK — 485 tests | stdout | Python 3.10 |
| pytest collect default | FAIL | falta suporte `--cov` | alinhar deps/ini |
| make test / fitness / API | Não executado | — | FASE 3 |
| FE build | Não executado | — | FASE 3 |

## 24. Alterações ainda não realizadas

- Hardening segurança  
- Correções FE  
- ADR payments  
- Wave 3  
- Commits  
- Docs FASE 8 adicionais (`project-current-state`, `unknowns-and-decisions`, `operational-readiness`, `decision-log`) — podem ser gerados na sequência se autorizados  

## 25. Decisões pendentes

1. Hospedagem e ownership da API.  
2. Staging real existe?  
3. Aprovar Sprint 1 hardening (IDs B-04).  
4. Prioridade FE 410 vs Wave 3.  
5. Versionar ou `.gitignore` os Prompt*/relatório.md na raiz.

## 26. Perguntas para stakeholders

1. `https://api.trancapro.com` está no ar? Quem opera?  
2. Existe staging da API? URL e DB?  
3. Keys AWS estáticas já removidas?  
4. PO: BeautyOS operação diária ou plataforma CoreFlow primeiro?  
5. Backup atual do banco (se houver)?  

## 27. Conclusão

A classificação **Amarelo** do relatório anterior **permanece adequada** após FASE 2: núcleo técnico e CI são sólidos no commit `e90df9e`, mas publicação da API, ambientes reais e hardening de segurança não estão comprovados no repositório. Payments write **confirma** divergência documental. Próximo passo seguro: **FASE 3 (execução local)** e, em paralelo, respostas dos stakeholders sobre deploy/ambientes — sem implementar hardening até listar IDs em `Prompt002`.
