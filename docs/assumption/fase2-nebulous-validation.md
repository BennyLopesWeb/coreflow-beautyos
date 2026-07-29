# FASE 2 — Validação de informações nebulosas

**Data:** 2026-07-28  
**Commit analisado:** `e90df9e`  
**Método:** somente leitura (código, Git, configs, `pytest --collect-only`)

Legenda de status: Confirmado · Parcialmente confirmado · Não confirmado · Contradito pelo código · Necessita validação externa

---

## Tabela consolidada N-01…N-10

| ID | Afirmação | Evidência encontrada | Status | Impacto | Próxima ação |
|----|-----------|----------------------|--------|---------|--------------|
| N-01 | Existe produção operacional da API | FE default prod `https://api.trancapro.com` (`frontend/src/config/api.ts`); TF `environments/prod` só módulo CDN; sem workflow deploy API; sem runbook API | **Necessita validação externa** | Alto | Confirmar com stakeholder se host responde e quem opera |
| N-02 | Existe homologação operacional | TF `staging` = CDN; D6 = `test_staging` + docs “staging-simulated”; sem URL/host staging API no repo | **Não confirmado** (API) / parcial (CDN as-code) | Alto | Mapear se há staging real fora do repo |
| N-03 | Deploy da API automatizado em cloud | `backend/Dockerfile` + compose local; workflows CI/test/CDN/EAS; **sem** ECS/K8s/PaaS no Terraform | **Confirmado:** build Docker local; **Deploy da API não identificado no repositório** | Crítico p/ go-live | Decidir plataforma de hospedagem |
| N-04 | Modelo de dados / migrações | SQLite default; MySQL CI + compose; Alembic `cf001`–`cf016`; DROP `agendamentos` histórico; backup/RTO/RPO ausentes em ops | **Parcialmente confirmado** | Alto | Documentar backup; validar MySQL local na FASE 3 |
| N-05 | Riscos SECRET_KEY / CORS | Defaults inseguros em `config.py`; JWT HS256 30min/7d; rate limit ausente; comprovante valida tipo+5MB | **Confirmado** (defaults) | Crítico se prod | Hardening Sprint 1 (após aprovação) |
| N-06 | Pagamentos Core vs legado / policy | Read: `modules/payments` flat + GET `/v1/payments`; Write: `PaymentReservationService` + `ComprovanteService` em `app/services`; Policy diz write hexagonal | **Contradito** (policy vs código) / write **legado de camada** com dados core | Alto | ADR alinhamento; não mover sem aprovação |
| N-07 | Legado coexiste com Core | Routers legado montados; FE ainda chama `/fila`, `/pagamentos/*`, `/agenda/*` em pontos; services ~20; models ~17–18 | **Confirmado** | Alto | Matriz de remoção antes de apagar |
| N-08 | Feature flags defaults | `FEATURE_BOOKING_CORE_ENABLED=True`; resource/AI/workflow/plugin OFF; enforcement `off` | **Confirmado** | Médio | Ativar só com testes + decisão |
| N-09 | Frontend alinhado /v1 | Booking lifecycle via `/v1/bookings`; comprovante `/v1/.../comprovante`; ainda legado fila/pagamentos/agenda update-delete; sem testes FE; EAS.json presente | **Parcialmente confirmado** | Alto | Inventariar rotas 410 quebradas no FE |
| N-10 | Testes | 69 arquivos; **485** testes coletados com `-o addopts=""`; `pytest.ini` exige `--cov` sem `pytest-cov` no ambiente local atual; FE sem testes app | **Parcialmente confirmado** | Médio | FASE 3: `make test` + fitness; instalar cov ou alinhar ini |

---

## N-01 — Produção

| Item | Achado |
|------|--------|
| URL | Hostname **pretendido** no FE: `https://api.trancapro.com` (não-dev). Liveness: **Necessita validação externa** |
| TF prod | Apenas `module "coreflow_cdn"` — não é prova de API em produção |
| Deploy API | Não identificado no repositório |
| Runbook operação API | Não identificado (existe `docs/ops/github-aws-oidc.md` para CI AWS) |
| Monitoramento live | Exports as-code; stack live não no compose principal |

## N-02 — Homologação

| Item | Achado |
|------|--------|
| Staging API hospedagem | Não identificado |
| Staging CDN | Env Terraform presente |
| Promoção | Gates docs + tags Version em reviews; promote API contínuo não identificado |
| D6 | Testes locais/simulados em `backend/tests/test_staging/` |

## N-03 — Deploy da API

**Deploy da API não identificado no repositório.**

Confirmado: Dockerfile Python 3.11-slim; `docker-compose.yml` sobe API local; CI build/test; mobile EAS separado; CDN sync via OIDC.

## N-04 — Banco

| Ambiente | Banco |
|----------|--------|
| Local default | SQLite (`DATABASE_URL` / compose `sqlite:///./data/coreflow.db`) |
| CI | MySQL 8 (`ci.yml`) |
| Staging/prod esperados | **Não confirmado** no repo |

Backup/restore/RTO/RPO: **Não identificado no repositório** (pasta `backups/` local histórica ≠ pipeline).

## N-05 — Segurança (severidades)

| Problema | Severidade | Evidência |
|----------|------------|-----------|
| `SECRET_KEY` default | Crítico (se não-dev) | `config.py` |
| `CORS_ORIGINS=["*"]` | Alto | `config.py` |
| Rate limiting ausente | Médio | busca sem hits |
| Upload comprovante | Baixo–Médio mitigado | tipo MIME + 5MB |
| CVE scan deps | Não avaliado | sem SCA no CI lido |
| Isolamento tenant | Parcialmente confirmado | `company_id` em deps/payments read |

Valores de secrets **não** exibidos.

## N-06 — Pagamentos

| Aspecto | Implementação |
|---------|----------------|
| Consulta | `PaymentService` → `core_payments`; `GET /v1/payments` |
| Escrita depósito/final | `app/services/payment_reservation_service.py` |
| Comprovante | `app/services/comprovante_service.py` + `POST /v1/bookings/{id}/comprovante` |
| Provider | `PaymentProviderPort` (protocol); adapters reais de gateway **não confirmados** como default |
| Webhook PIX | `POST /webhook/pix` existe (router) |
| FE | comprovante core; ainda há calls `/pagamentos/sinal*` |

**vs docs:** `ModuleTieringPolicy` afirma payments write = CORE hexagonal — **contradito** pela localização atual do write path (services legado + docstring do provider admitindo bridge legado).

## N-07 — Matriz legado × Core (amostra)

| Item legado | Consumidores | Equivalente Core | Risco de remoção | Ação recomendada |
|-------------|--------------|------------------|------------------|------------------|
| `GET/POST /fila*` | FE `filaService`, admin | queue + booking linkage parcial | Alto | Migrar FE antes de remover |
| `/pagamentos/sinal*` | FE `pagamentoService` | admin confirmar-sinal booking + v1 comprovante | Alto | Remover calls FE mortas |
| `PUT/DELETE /agenda/agendamentos` | FE `agendamentoService` | `/v1/bookings` reschedule/cancel | Alto | Trocar FE; validar 410 |
| `app/services/*` (~20) | routers/admin | modules/* | Alto | Sunset incremental |
| `payments` table ORM | services | `core_payments` + bridge | Alto | Manter até conciliação |
| Models `cliente`/`tranca` | legado + ACL | `core_customers` / resources | Médio | ACL até parity |

## N-08 — Feature flags (principais)

| Flag | Default | Finalidade | Código pronto? | Testes | Pode ativar? | Condições |
|------|---------|------------|----------------|--------|--------------|-----------|
| `FEATURE_BOOKING_CORE_ENABLED` | True | Booking core write | Sim (pós R3/R4) | Amplos R2–R4 | Sim (já default) | Kill-switch emergência |
| `FEATURE_RESOURCE_ENGINE_ENABLED` | False | Resource engine | Parcial | test_r2_f3* | Só com P11 + decisão | Flag OFF = path antigo |
| `FEATURE_AI_CORE_ENABLED` | False | AI core | Parcial/mock | cf7/cf8 | Não em prod sem provider | `AI_LLM_*` |
| `FEATURE_WORKFLOW_ENABLED` | False | Workflows | Parcial | cf8 | Não sem validação | — |
| `FEATURE_PLUGIN_ENGINE_ENABLED` | False | Plugin engine avançado | Parcial | cf11 | Não sem DoR | — |
| `FEATURE_LEGACY_TELEMETRY_ENABLED` | False | Telemetria legado | — | — | Irrelevante p/ go-live | — |
| `CORE_ENFORCEMENT_MODE` | off | Bloquear paths legado | Sim R3 | test_r3_f1* | Staging/prod: avaliar `block` | FE legado ainda chama rotas |
| `CORE_ENFORCEMENT_WARN_ENABLED` | True | Warn mode | Sim | — | Dev ok | — |
| `LEGACY_SUNSET_ENABLED` | True | Headers sunset | Sim | test_legacy_sunset | Sim | Data 2028 |
| `AI_LLM_ENABLED` | False | LLM | Mock default | — | Não | Chave OpenAI |
| `RABBITMQ_ENABLED` / `KAFKA_ENABLED` | False | Bus | Opcional | cf13+ | Só com infra | compose overlays |
| `CDN_S3_ENABLED` | False | Sync S3 | Scripts/CI | — | Ops | OIDC |
| `OTEL_ENABLED` | False | Tracing | Deps presentes | — | Opcional | collector |
| `MOBILE_CDN_ENABLED` | True | CDN mobile config | Sim | — | Ok se host real | — |

## N-09 — Frontend

- Auth: `/auth/login|register|me|refresh` — presente.
- Booking: `reservationService` e listagens `/v1/bookings` — presente.
- Comprovante: path core R4-F15 — presente.
- Legado ativo: fila, alguns pagamentos, update/delete agenda.
- Testes app: **não encontrados** (fora node_modules).
- EAS: `eas.json` profiles development/preview/production.
- Compilação nesta sessão: **não executada**.

## N-10 — Testes

| Métrica | Valor |
|---------|--------|
| Arquivos `test_*.py` | 69 |
| Casos coletados | **485** (`pytest --collect-only -q -o addopts=""`) |
| Execução pass/fail | **Não executada** nesta fase (só collect) |
| Coverage tool local | `pytest.ini` pede `--cov` mas collect falha sem override → provável ausência `pytest-cov` |
| CI | Usa `-o addopts=""` (evita cov) |
| FE / E2E | Não identificados no app |
