# LEGACY-EVIDENCE-DRY-RUN — Runbook (somente leitura)

Auditoria de `Payment` DEPOSIT/SINAL `PENDING` que ainda podem carregar
`valor = booking.deposit_amount` após o PR #47.

Código integrado pelo PR #48:

- `backend/app/modules/payments/legacy_evidence_audit.py`
- `backend/scripts/audit_legacy_evidence_pending.py`

Esta operação é **exclusivamente read-only**. Não autoriza backfill.

## Pré-requisitos

- Branch/`main` contendo o PR #48 (ou posterior).
- Acesso a um DSN de **staging** com credencial **somente leitura**.
- Python/venv do `backend` operacional.
- Autorização explícita para consulta read-only em staging.
- Produção **fora de escopo** desta etapa.

## Ambiente permitido

| Ambiente | Permitido nesta etapa |
|---|---|
| staging (read-only) | Sim, com checklist completo |
| produção | Não |
| SQLite local (`trancapro.db`) | Não — não é staging |

## Variável de ambiente esperada

O script usa `SessionLocal` de `app.db.session`, que lê
`settings.DATABASE_URL` (`app.core.config.Settings`).

- Variável: **`DATABASE_URL`**
- Não há suporte a `STAGING_DATABASE_URL` nem `READONLY_DATABASE_URL` no código atual.
- Não há flag CLI para escolher ambiente; o alvo é o `DATABASE_URL` do processo.
- O engine SQLAlchemy é criado no import: a variável precisa existir **antes**
  de iniciar o Python.

Não inventar variáveis novas. Não alterar configuração da aplicação para esta
operação.

## Como injetar o DSN sem gravá-lo em arquivo

Preferir injeção pontual no comando (não export permanente no shell, não
`.env` versionado, não commit).

```bash
cd backend

DATABASE_URL='<injetado de forma segura pelo ambiente>' \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-staging.json
```

Alternativas seguras (quando disponíveis):

- secret manager / vault com injeção de env no job;
- CI/CD com secret efêmero;
- wrapper do operador que exporta apenas na sessão autorizada.

Não:

- colar DSN em commit, PR, issue ou chat;
- gravar DSN em `.env` do repositório;
- redirecionar logs contendo DSN para artefato versionado.

## Como confirmar que o alvo é staging

Antes de executar, confirmar por canal operacional (fora do relatório público):

1. host/endpoint corresponde ao staging conhecido;
2. nome do schema/database é o de staging;
3. usuário é de leitura (sem grants de `UPDATE`/`INSERT`/`DELETE`);
4. o DSN **não** aponta para produção;
5. o DSN **não** é SQLite local.

O relatório final deve registrar apenas:

- ambiente = `staging`;
- confirmação de read-only = sim;
- sem imprimir host completo, usuário, senha ou query string.

## Checklist de autorização (obrigatório)

Se qualquer item falhar, **não executar**.

- [ ] ambiente confirmado como staging;
- [ ] DSN fornecido por canal seguro;
- [ ] credencial possui somente leitura;
- [ ] banco e schema corretos confirmados;
- [ ] backup não é necessário porque não haverá escrita;
- [ ] `--dry-run` será usado;
- [ ] nenhuma flag de mutação será usada;
- [ ] saída não contém dados pessoais ou URLs privadas;
- [ ] horário da execução será registrado em UTC;
- [ ] executor e commit serão registrados;
- [ ] produção não será consultada nesta etapa;
- [ ] SQLite local não será usado como substituto.

## Checklist de infraestrutura AWS (teste final)

Para dry-run via **AWS Secrets Manager**, completar **antes** de qualquer
`get-secret-value` ou consulta ao banco. Não preencher com valores inventados.

- [ ] conta AWS confirmada pelo responsável de infraestrutura (staging CoreFlow);
- [ ] role de execução confirmada;
- [ ] região AWS confirmada;
- [ ] secret ARN/nome confirmado;
- [ ] secret possui metadado `environment=staging` (ou equivalente acordado);
- [ ] secret não pertence à produção;
- [ ] permissão IAM limitada a `secretsmanager:GetSecretValue` (mínimo necessário);
- [ ] credencial do banco é somente leitura;
- [ ] database/schema de staging confirmados;
- [ ] formato do `SecretString` confirmado (A ou B — ver abaixo);
- [ ] `DATABASE_URL` será injetada somente no processo (sem `export` persistente);
- [ ] nenhum segredo será gravado em disco;
- [ ] `--dry-run` será usado;
- [ ] `--apply` e `--backfill` não serão usados;
- [ ] identidade `Curso-bedrock` (ou equivalente de curso/treino) **não** será usada.

Plano detalhado: `docs/operations/STAGING-LEGACY-EVIDENCE-FINAL-TEST-PLAN.md`.

## Contrato do secret (placeholders — sem valores reais)

A resolução AWS permanece **externa** ao backend. O script continua dependendo
apenas de `DATABASE_URL`. Não adicionar SDK AWS à aplicação para esta operação.

Não assumir o formato final sem confirmação da infraestrutura.

### Formato A — SecretString JSON com URL completa

```json
{
  "DATABASE_URL": "<staging-read-only-database-url>"
}
```

### Formato B — SecretString JSON com campos de conexão

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

Regras:

- o secret deve representar **staging**;
- o usuário SQL deve ter **somente leitura**;
- o secret não deve conter credenciais de produção;
- ARN real só deve ser commitado se a política interna permitir (preferir
  placeholder no git);
- o valor nunca deve aparecer em logs, PRs ou relatórios.

## Comando de dry-run

Injeção genérica (canal seguro já resolveu a URL):

```bash
cd backend

# Opcional: registrar commit da aplicação
git rev-parse HEAD

DATABASE_URL='<injetado de forma segura pelo ambiente>' \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-staging.json
```

### Padrão futuro via AWS Secrets Manager (não executar sem checklist completo)

Se a infra confirmar que `SecretString` **é a URL pura**:

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

Se o secret for JSON (Formato A ou B), extrair `DATABASE_URL` (ou montar a URL)
com ferramenta/local acordada pela infra, **em memória**, sem gravar em arquivo
e sem `echo`/`env`/`printenv`/`set -x`. Confirmar o parsing antes do teste final;
não inventar parser no repositório sem necessidade.

Antes de iniciar o Python, garantir (sem imprimir) que o valor injetado **não**
é SQLite (`sqlite:`). O default local da aplicação (`sqlite:///./trancapro.db`)
**não** é staging — ausência de injeção explícita bloqueia o teste real.

Não usar:

```bash
export DATABASE_URL=...
echo "$DATABASE_URL"
env
printenv
set -x
```

Não salvar o resultado de `get-secret-value` em arquivo temporário.

Validação de flags (deve falhar com exit ≠ 0):

```bash
python scripts/audit_legacy_evidence_pending.py --apply
python scripts/audit_legacy_evidence_pending.py --backfill
```

Esperado: mensagem de erro e exit code `2`.

## Validação de que nenhuma flag mutável foi usada

Antes e depois:

```bash
# histórico da sessão / comando deve mostrar apenas --dry-run
# e opcionalmente --json-out / --limit
```

Proibido:

```bash
python scripts/audit_legacy_evidence_pending.py --apply
python scripts/audit_legacy_evidence_pending.py --backfill
```

O script rejeita essas flags. Se alguma for aceita no futuro, **interromper**
e reportar.

## Saída esperada

JSON agregado com (entre outros):

- `dry_run: true`
- `mutation: false`
- `counts.candidate_backfill`
- `counts.review_required`
- `counts.exclude_legitimate`
- `counts.already_clean`
- `candidate_ids` / `review_ids` (somente IDs internos)
- `universe.*` (contagens)
- `reason_frequency`
- `cutoff_utc`

Interpretar:

| Classe | Ação |
|---|---|
| `candidate_backfill` | Não autoriza alteração; apenas candidatura |
| `review_required` | Revisão humana; sem mutação automática |
| `exclude_legitimate` | Não alterar |
| `already_clean` | Já com placeholder `0.00` |

## Dados que não devem ser registrados

- DSN, senha, token, query string;
- URLs privadas de comprovantes;
- nomes, e-mails, documentos;
- dumps de tabela;
- valores sensíveis por registro além do necessário para contagem.

Permitido no relatório: contagens, IDs internos, motivos agregados, UTC,
commit SHA, nome do executor.

## Procedimento de interrupção

Se houver qualquer sinal de escrita, erro de autenticação inesperado, ou
dúvida sobre o ambiente:

1. interromper imediatamente (Ctrl+C / cancelar job);
2. não repetir o comando;
3. registrar horário UTC e ambiente (`staging`);
4. preservar logs técnicos **sem** credenciais;
5. reportar ao responsável antes de nova tentativa.

## Procedimento de limpeza

- manter `/tmp/legacy-evidence-audit-staging.json` fora do git;
- não commitar a saída;
- apagar o JSON temporário quando o relatório agregado já tiver sido
  transcrito com segurança;
- não deixar `DATABASE_URL` exportado na sessão após o uso.

## Relatório final sugerido

Após a execução autorizada, registrar:

1. ambiente (`staging`), UTC, commit, executor;
2. comando (sem DSN);
3. confirmação `--dry-run` e ausência de flags mutáveis;
4. contagens principais;
5. distribuição por motivo (se disponível);
6. confirmação de não-mutação / working tree intacta;
7. recomendação (nenhum backfill / backfill controlado / revisão manual),
   **sem executar** backfill nesta etapa.

## Próximo passo após o dry-run

1. analisar contagens;
2. se zero candidatos → manter correção por reupload;
3. se candidatos inequívocos → propor backfill em PR/autorização **separada**;
4. se ambiguidades relevantes → revisão manual;
5. produção só com autorização explícita futura (fora deste runbook).
