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

## Comando de dry-run

```bash
cd backend

# Opcional: registrar commit da aplicação
git rev-parse HEAD

DATABASE_URL='<injetado de forma segura pelo ambiente>' \
python scripts/audit_legacy_evidence_pending.py \
  --dry-run \
  --json-out /tmp/legacy-evidence-audit-staging.json
```

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
