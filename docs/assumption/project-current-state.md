# Estado atual do projeto — Assunção técnica

**Referência de código:** `b632ea8708ea860d1c0706b87b61a1b0750bfc29`  
**Data do documento:** 2026-07-28  
**Classificação das afirmações:** Fato · Inferência · Pendência

---

## Identidade

| Campo | Valor | Tipo |
|-------|--------|------|
| Produto | CoreFlow Platform / plugin BeautyOS | Fato |
| Branch local | `main` @ `b632ea8` | Fato |
| `origin/main` | `e90df9e` (local **ahead 1**) | Fato |
| Versão app | `2.20.0-r4-f17` | Fato (`config.py`) |
| Tag Git mais recente | `v1.20.1-r2-f2b` | Fato (desalinhada da versão) |

---

## Funcionalidades confirmadas (local)

| Área | Resultado | Evidência |
|------|-----------|-----------|
| Suite pytest | **485 passed** | FASE 3 / `make test` |
| Architecture fitness F5 | **PASS** | `make fitness` |
| Health | OK | `GET /health` |
| Platform health | OK · versão 2.20.0-r4-f17 | `GET /v1/platform/health` |
| Auth register/login/me | OK | smoke FASE 3 |
| Booking create/get/cancel | OK (datetime naive) | smoke FASE 3 |
| Booking com `scheduled_at` + `Z` | **Corrigido** em `b632ea8` | testes `test_r2_f1_booking_create.py` (10 passed) |
| Payments read | Módulo flat + `GET /v1/payments` | código / Ledger P8 |
| Fila legado | `GET /fila/{date}` responde | smoke FASE 3 |

---

## Funcionalidades parciais

| Área | Situação | Tipo |
|------|----------|------|
| Frontend | Usa `/v1/bookings` e ainda chama rotas legado (`/fila`, `/pagamentos/*`, agenda) | Fato |
| Resource/AI/Workflow engines | Flags OFF por padrão | Fato |
| Enforcement | Default `off` / warn | Fato |
| CDN / OIDC CI | Implementado as-code | Fato |
| Payments write | Em `app/services` (bridge), não hexagonal completo | Fato vs policy |

---

## Pendências

| Item | Tipo |
|------|------|
| Push/PR do commit `b632ea8` | Pendência |
| Staging/produção API comprovados | Pendência / validação externa |
| Deploy da API no repositório | Pendência — **não identificado** |
| Hardening `SECRET_KEY` / CORS | Pendência |
| Versionar docs de assunção (este pacote) | Pendência |
| Wave 3 OPS | Pendência — só com prioridade PO |

---

## Ambiente de desenvolvimento

| Item | Valor | Tipo |
|------|--------|------|
| Python validado | 3.11.13 + `backend/.venv` | Fato |
| DB local FASE 3 | SQLite via `make migrate` | Fato |
| MySQL | Validado no CI; não reexecutado nesta máquina na FASE 3 | Fato / Pendência local |
| `.env` | A partir de `.env.example` (gitignored) | Fato |

---

## Riscos abertos (resumo)

1. Deploy API ausente no repo — bloqueia go-live auditável.  
2. Defaults de segurança (`SECRET_KEY`, CORS `*`) — crítico se usados em não-dev.  
3. FE legado vs rotas 410.  
4. Ambientes reais não comprovados.  
5. Bus factor / documentação executiva desatualizada.

---

## Limitações deste documento

- Não substitui runbook de produção.  
- Não afirma que `api.trancapro.com` está no ar (apenas hostname no FE).  
- Não inclui secrets nem dados pessoais.  
- Working tree pode conter untracked/modificados fora de `b632ea8` — ver classificação FASE A.
