# Ensaio local MySQL — auditoria de evidência legada

Este documento descreve um **ensaio local com dados sintéticos** no MySQL
Docker já existente no repositório.

**Não é staging. Não autoriza backfill. Não substitui o dry-run real.**

Referências:

- Script de auditoria: `backend/scripts/audit_legacy_evidence_pending.py`
- Seed sintético: `backend/scripts/seed_legacy_evidence_local.py`
- Runbook staging: `docs/operations/LEGACY-EVIDENCE-DRY-RUN.md`
- Plano staging: `docs/operations/STAGING-LEGACY-EVIDENCE-FINAL-TEST-PLAN.md`

---

## Escopo

| Item | Valor |
|---|---|
| Ambiente | Docker MySQL local |
| Dados | Sintéticos (`LOCAL_AUDIT_SEED`) |
| Staging | Não |
| Produção | Não |
| AWS / Secrets Manager | Não |
| SQLite como alvo do ensaio | Não |

Credenciais do compose MySQL (`coreflow` / `coreflow`) são **somente teste
local**, já versionadas no overlay — não são staging/prod.

---

## Subida do MySQL

Preferir o Makefile quando a porta **3306 do host estiver livre**:

```bash
make docker-mysql-up
```

Equivalente:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build
```

Isso sobe:

- serviço `mysql` (MySQL 8.0, porta host `3306`, healthcheck);
- serviço `api` (entrypoint tenta `alembic upgrade head` — ver seção de schema).

Aguardar health:

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml ps
```

### Porta 3306 ocupada no host

Se existir `mysqld` nativo (ou outro processo) em `3306`, use o overlay de
ensaio (somente remap de porta; credenciais locais inalteradas):

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml up -d --build
```

Nesse caso o host acessa `127.0.0.1:3307` → container `3306`. Dentro da rede
Docker, a API continua em `mysql:3306`.

---

## Preparação do schema

Em volume MySQL **novo**, o entrypoint só com `alembic upgrade head` pode
falhar (FK `core_*` → `companies`). O procedimento existente (igual ao CI
`test-mysql`) é bootstrap via `init_db()`:

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml \
  run --rm --no-deps \
  -e DATABASE_URL='mysql+pymysql://coreflow:coreflow@mysql:3306/coreflow?charset=utf8mb4' \
  api python -c "from app.db.init_db import init_db; init_db()"
```

Isso executa `Base.metadata.create_all` (legado) e em seguida Alembic head.
Não altera migrations versionadas.

Se a porta host for `3306` (sem overlay) e o host tiver `pymysql`:

```bash
cd backend
DATABASE_URL='mysql+pymysql://coreflow:coreflow@127.0.0.1:3306/coreflow?charset=utf8mb4' \
  python -c "from app.db.init_db import init_db; init_db()"
```

---

## Seed

Preferir execução no container (host validado pelo script: `mysql`):

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml \
  run --rm --no-deps \
  -e DATABASE_URL='mysql+pymysql://coreflow:coreflow@mysql:3306/coreflow?charset=utf8mb4' \
  api python scripts/seed_legacy_evidence_local.py
```

Alternativa no host (ajuste a porta se usar o overlay `3307`):

```bash
cd backend
DATABASE_URL='mysql+pymysql://coreflow:coreflow@127.0.0.1:3307/coreflow?charset=utf8mb4' \
  python scripts/seed_legacy_evidence_local.py
```

O seed:

- exige MySQL em `127.0.0.1`, `localhost` ou host Docker `mysql`;
- rejeita SQLite, staging, produção e hosts RDS;
- é idempotente (marcadores `LOCAL_AUDIT_SEED`);
- cria tenants `local-audit-tenant-a-001` e `local-audit-tenant-b-001`.

### Cenários

| Caso | Marcador | Resultado esperado na auditoria |
|---|---|---|
| A | candidate (cotação em PENDING) | `candidate_backfill` |
| B | evidência `0.00` | `already_clean` |
| C | `PAID` | `exclude_legitimate` |
| D | `deposit_paid=true` + PENDING | `REVIEW_REQUIRED` |
| E | tenant B candidato | `candidate_backfill` (outro tenant) |

---

## Execução do dry-run local

Via container (recomendado no ensaio com overlay):

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml \
  run --rm --no-deps \
  -e DATABASE_URL='mysql+pymysql://coreflow:coreflow@mysql:3306/coreflow?charset=utf8mb4' \
  -v /tmp:/tmp \
  api python scripts/audit_legacy_evidence_pending.py \
    --dry-run \
    --json-out /tmp/legacy-evidence-audit-local-mysql.json
```

Via host (porta `3306` livre, ou `3307` com overlay):

```bash
cd backend
DATABASE_URL='mysql+pymysql://coreflow:coreflow@127.0.0.1:3307/coreflow?charset=utf8mb4' \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-local-mysql.json
```

Não usar `--apply` nem `--backfill`.

O JSON deve permanecer **fora do Git**.

---

## Resultado esperado

O relatório deve refletir os casos sintéticos do seed (além de quaisquer
outros DEPOSIT/SINAL já presentes no volume local). Em volume limpo + seed:

- pelo menos 2 `candidate_backfill` (casos A e E);
- 1 `already_clean` (B);
- 1 `exclude_legitimate` (C);
- 1 `review_required` (D).

Interpretar apenas como validação da lógica local — **não** como evidência de
staging.

---

## Limpeza segura

Somente dados marcados `LOCAL_AUDIT_SEED`:

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml \
  run --rm --no-deps \
  -e DATABASE_URL='mysql+pymysql://coreflow:coreflow@mysql:3306/coreflow?charset=utf8mb4' \
  api python scripts/seed_legacy_evidence_local.py --cleanup
```

Não usar:

- `docker system prune`
- remoção ampla de volumes não relacionados
- `rm -rf` sobre dados fora do ensaio

Para derrubar a stack (opcional; não remove o volume `mysql_data` por padrão):

```bash
docker compose -f docker-compose.yml \
  -f docker-compose.mysql.yml \
  -f docker-compose.mysql.rehearsal.yml down
```

Ou, sem overlay: `make docker-mysql-down`.

---

## Limitações

- não substitui staging;
- resultados são sintéticos;
- secret real / role AWS / SQL read-only de staging **não** foram validados;
- contagens **não** autorizam backfill real.
