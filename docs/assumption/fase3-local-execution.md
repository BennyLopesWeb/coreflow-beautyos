# FASE 3 — Validação de execução local

**Data:** 2026-07-28 (~22:06–22:15 -03)  
**Commit:** `e90df9e`  
**Python:** 3.11.13 (`backend/.venv`)  
**Escopo:** local only — sem commit, sem alteração de código de produto

---

## Preparação

| Etapa | Resultado | Evidência |
|-------|-----------|-----------|
| Criar venv 3.11 | OK | `backend/.venv` |
| `pip install -r requirements.txt` | OK | install completo |
| `pip install pytest-cov` | OK | necessário p/ `pytest.ini` |
| `cp .env.example .env` | OK | gitignored |
| `make migrate` | OK | tenant `salao-demo`, sync metamodelo |

---

## Tabela de resultados (Prompt001 FASE 3)

| Etapa | Comando/endpoint | Resultado | Evidência | Problema | Severidade |
|-------|------------------|-----------|-----------|----------|------------|
| Testes | `make test` (venv 3.11) | **PASS** | `485 passed` em 167s | warnings pydantic/sqlalchemy | Baixo |
| Fitness | `make fitness` | **PASS** | `architecture_fitness_check: PASS (F5)` | — | — |
| Health | `GET /health` | **PASS** | `{"status":"healthy"}` HTTP 200 | — | — |
| Platform health | `GET /v1/platform/health` | **PASS** | version `2.20.0-r4-f17`, plugin beauty active | — | — |
| Plugins | `GET /v1/plugins` | **PASS** | beauty + stubs | — | — |
| Register (payload errado) | `POST /auth/register` com `full_name` | **FAIL esperado** | 422 — exige `nome`,`telefone` | Docs/FE podem usar nomes errados | Médio (docs) |
| Register correto | `POST /auth/register` UserCreate | **PASS** | 201 | — | — |
| Login | `POST /auth/login` | **PASS** | JWT access+refresh | — | — |
| Me | `GET /auth/me` | **PASS** | 200 | role inicial `customer` | — |
| Customers/Bookings como customer | `GET /v1/customers`, `/v1/bookings` | **403** | RBAC admin/owner | esperado | — |
| Promoção local owner | update DB smoke user | OK (local) | role `owner` | só para smoke | — |
| List customers (owner) | `GET /v1/customers` | **PASS** | 7 customers | — | — |
| Create booking (sem Idempotency-Key) | `POST /v1/bookings` | **400** | `idempotency_key_required` | contrato exige header | Médio (DX) |
| Create booking (datetime com `Z`) | `POST /v1/bookings` | **400** | `can't compare offset-naive and offset-aware datetimes` | bug timezone | **Alto** |
| Create booking (slot ocupado) | `POST /v1/bookings` | **409** | `slot_unavailable` | esperado | — |
| Create booking (slot livre) | `POST /v1/bookings` + Idempotency-Key | **PASS** | 201 id=6 `pending_payment` | — | — |
| Get booking | `GET /v1/bookings/6` | **PASS** | 200 | — | — |
| Cancel booking | `POST /v1/bookings/6/cancel` | **PASS** | 200 `cancelled` | — | — |
| Payments list | `GET /v1/payments?booking_id=1` | **PASS** | 200 `[]` | sem pagamento naquele booking | Baixo |
| Fila legado | `GET /fila/{date}` | **PASS** | 200 | — | — |
| Comprovante upload | — | **Não executado** | — | multipart não coberto neste smoke | — |
| Frontend compile | — | **Não executado** | — | fora do escopo desta rodada | — |
| MySQL docker | — | **Não executado** | — | SQLite validado; CI cobre MySQL | — |

---

## Problemas encontrados (locais)

1. **Timezone naive vs aware no create booking** — request com `...Z` (offset-aware) falha 400. Severidade: Alta para clientes que enviam ISO-8601 com timezone.  
2. **Idempotency-Key obrigatório** — 400 se ausente (comportamento documentável; não é bug se intencional).  
3. **Register schema** — campos `nome`/`telefone` (não `full_name`); risco de docs desatualizados.  
4. **Availability query** — formato `date` exige datetime com separador `T`, não só `YYYY-MM-DD` (DX).  
5. **pytest-cov** não está em `requirements.txt` mas é exigido por `pytest.ini` (CI contorna com `-o addopts=""`).

---

## Ambiente após FASE 3

| Artefato | Status |
|----------|--------|
| `backend/.venv/` | criado (gitignored) |
| `backend/.env` | criado a partir do example (gitignored) |
| DB SQLite local | migrado/seed sync (`trancapro.db`) |
| Usuário smoke | `fase3.local@example.com` (promovido a owner **somente local**) |

---

## Conclusão FASE 3

Execução local **confirmada** para o núcleo: deps, 485 testes, fitness F5, API health, auth, listagens owner, create+cancel booking.  

Bloqueio funcional observado no smoke: comparação de datetime timezone no `POST /v1/bookings`.  

**Follow-up B-TZ (2026-07-28):** corrigido — `as_naive_utc` + normalização em `BookingDomainService.create` e `DisponibilidadeService`; regressão em `test_r2_f1_booking_create.py` (10 passed + fitness F5). Aguardando aprovação de commit.
