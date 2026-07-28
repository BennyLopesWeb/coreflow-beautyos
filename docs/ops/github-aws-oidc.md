# GitHub Actions → AWS via OIDC (R4-F16 / R4-F17)

Substitui secrets estáticos `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` por
assumção de role (`AWS_ROLE_ARN`) via OIDC.

## Provisionar com Terraform (R4-F17)

```bash
# Requer credenciais AWS locais (ou profile) com permissão IAM
./scripts/terraform-ci-oidc.sh plan
./scripts/terraform-ci-oidc.sh apply
```

Stack: `infra/terraform/environments/ci-oidc`  
Módulo: `infra/terraform/modules/github-oidc`

O `apply` imprime o ARN — copie para o secret GitHub `AWS_ROLE_ARN`.

## GitHub

| Tipo | Nome | Valor |
|------|------|-------|
| Secret | `AWS_ROLE_ARN` | output `aws_role_arn` do stack `ci-oidc` |
| Variable | `AWS_REGION` | `us-east-1` (ou região do provider) |

Workflows afetados:

- `.github/workflows/terraform-cdn.yml`
- `.github/workflows/cdn-sync.yml`
- `.github/workflows/terraform-drift.yml` (job `plan-drift`)

Action compartilhada: `.github/actions/configure-aws-oidc`.

Após validar OIDC, **remover** `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`
dos secrets do repositório.

O provider IAM usa o issuer `token.actions.githubusercontent.com`
(`https://token.actions.githubusercontent.com`).

## Validação

1. `./scripts/terraform-ci-oidc.sh apply`
2. Configurar `AWS_ROLE_ARN` + `AWS_REGION` no GitHub
3. `workflow_dispatch` em **CoreFlow Terraform CDN** com `plan` / env `dev`
4. Confirmar logs: `AssumeRoleWithWebIdentity` sem access keys
5. Remover secrets estáticos
