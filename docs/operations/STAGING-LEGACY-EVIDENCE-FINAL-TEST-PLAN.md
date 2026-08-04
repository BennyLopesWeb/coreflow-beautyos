# Plano de teste final — dry-run staging (legacy evidence)

Planejamento operacional para executar o dry-run de
`backend/scripts/audit_legacy_evidence_pending.py` em **staging**, com DSN
lido do **AWS Secrets Manager** e injetado apenas na memória do processo.

Este documento **não autoriza** a execução. É o plano a seguir após a
infraestrutura confirmar conta, role, secret e SQL read-only.

Referências:

- Runbook: `docs/operations/LEGACY-EVIDENCE-DRY-RUN.md`
- Classificação: `docs/architecture/AUDIT-LEGACY-EVIDENCE-PENDING-01.md`
- Base de código: `main` ≥ PR #49 (`7ea2bb8` ou posterior)

---

## Pré-requisitos

Preencher somente com valores confirmados pela infraestrutura (não inventar):

| Item | Valor confirmado | Status |
|---|---|---|
| Conta AWS correta (staging CoreFlow) | _pendente_ | [ ] |
| Role de execução | _pendente_ | [ ] |
| Região AWS | _pendente_ | [ ] |
| Secret nome ou ARN | _pendente_ | [ ] |
| Metadado `environment=staging` | _pendente_ | [ ] |
| Permissão `secretsmanager:GetSecretValue` | _pendente_ | [ ] |
| Formato do `SecretString` (A ou B) | _pendente_ | [ ] |
| Usuário SQL somente leitura | _pendente_ | [ ] |
| Database/schema de staging | _pendente_ | [ ] |

### Identidades / alvos proibidos nesta etapa

| Item | Regra |
|---|---|
| `arn:aws:iam::756264933198:user/Curso-bedrock` | **Não usar** como staging CoreFlow |
| Produção | Fora de escopo |
| SQLite local | Não é staging |
| Conta/role não confirmada | Interromper |

---

## Pré-checagens

Executar na ordem. Qualquer falha → **parar**.

1. Repositório

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git status --short
```

2. Identidade AWS (apenas metadados de caller; sem ler secret)

```bash
aws sts get-caller-identity
```

Confirmar verbalmente com infra que Account/Arn são os de **staging CoreFlow**.
Não prosseguir se a identidade for `Curso-bedrock` ou produção.

3. Metadados do secret (sem valor)

```bash
aws secretsmanager describe-secret \
  --secret-id "<STAGING_SECRET_ARN_OU_NOME>" \
  --query "{Name:Name,ARN:ARN,Tags:Tags,Description:Description}" \
  --output json
```

Confirmar:

- tag/metadado `environment=staging` (ou equivalente acordado);
- ausência de indício de produção;
- ARN/nome batem com o pré-requisito preenchido.

4. Interface do script (sem banco)

```bash
cd backend
python scripts/audit_legacy_evidence_pending.py --help
```

5. Working tree: ruído local pré-existente é aceitável; **não** commitar saída
   do dry-run.

---

## Execução (futura — não executar neste plano)

### Contrato do secret (placeholders)

#### Formato A — URL completa em JSON

```json
{
  "DATABASE_URL": "<staging-read-only-database-url>"
}
```

#### Formato B — campos de conexão

```json
{
  "engine": "postgresql",
  "host": "<staging-db-host>",
  "port": 5432,
  "dbname": "<staging-database>",
  "username": "<readonly-user>",
  "password": "<secret>"
}
```

O formato final **deve** ser confirmado pela infraestrutura antes da execução.
Não assumir A ou B.

### Injeção segura (Formato A — SecretString JSON com chave DATABASE_URL)

Adaptação conceitual (confirmar parsing com infra; não inventar parser no app):

```bash
cd backend

# Pseudopadrão: extrair DATABASE_URL do JSON em memória e injetar só no processo.
# Não usar echo/env/printenv/set -x. Não gravar em arquivo.
DATABASE_URL="$(
  aws secretsmanager get-secret-value \
    --secret-id "<STAGING_SECRET_ARN>" \
    --query 'SecretString' \
    --output text \
  | <extrator_local_confirmado_pela_infra>
)" \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-staging.json
```

### Injeção segura (SecretString = URL pura)

Somente se a infra confirmar que `SecretString` **é** a URL completa:

```bash
cd backend

DATABASE_URL="$(
  aws secretsmanager get-secret-value \
    --secret-id "<STAGING_SECRET_ARN>" \
    --query 'SecretString' \
    --output text
)" \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-staging.json
```

### Proibido na execução

```bash
export DATABASE_URL=...
echo "$DATABASE_URL"
env
printenv
set -x
python scripts/audit_legacy_evidence_pending.py --apply
python scripts/audit_legacy_evidence_pending.py --backfill
```

Não salvar `get-secret-value` em arquivo temporário.

Antes de rodar o Python, confirmar (sem imprimir a URL) que o valor injetado
**não** começa com `sqlite:`.

---

## Validação pós-execução

Coletar somente agregados:

- total analisado;
- `candidate_backfill`;
- `REVIEW_REQUIRED`;
- excluídos / `already_clean`;
- divergências Payment/CorePayment (via motivos);
- `dry_run: true` e `mutation: false`;
- zero dados sensíveis no relatório.

Também:

```bash
git status --short
git diff --check
```

Remover `/tmp/legacy-evidence-audit-staging.json` após transcrever contagens.

---

## Critérios de falha (interromper)

- conta AWS / role não confirmadas como staging CoreFlow;
- identidade `Curso-bedrock` ou equivalente de curso/treino;
- ambiente não é staging;
- secret sem metadado esperado;
- secret/ambiente de produção;
- credencial SQL não é read-only;
- `DATABASE_URL` ausente ou SQLite;
- erro de autenticação AWS/DB;
- caminho de escrita no script/app;
- output expõe segredo;
- qualquer indício de mutação no banco;
- uso de `--apply` / `--backfill`.

---

## Pós-teste

1. Registrar UTC, commit SHA, Account/Arn AWS (sem credenciais).
2. Manter somente contagens agregadas.
3. Remover artefato temporário.
4. **Não** executar backfill.
5. Abrir decisão separada:
   - zero candidatos → reupload;
   - candidatos inequívocos → tarefa de backfill controlado;
   - ambiguidades → revisão manual.

---

## Escopo negativo deste plano

- não cria secret;
- não altera IAM;
- não altera Terraform de produção;
- não altera `Payment` / `CorePayment`;
- não cria migration, backfill ou writer `PAID`;
- não adiciona SDK AWS ao backend (resolução permanece externa).
