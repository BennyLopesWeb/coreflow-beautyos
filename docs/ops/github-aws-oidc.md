# GitHub Actions → AWS via OIDC (R4-F16)

Substitui secrets estáticos `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` por
assumção de role (`AWS_ROLE_ARN`) via OIDC.

## GitHub

| Tipo | Nome | Valor |
|------|------|-------|
| Secret | `AWS_ROLE_ARN` | ARN da role IAM (ex. `arn:aws:iam::ACCOUNT:role/coreflow-github-actions`) |
| Variable | `AWS_REGION` | Região (default nos workflows: `us-east-1`) |

Workflows afetados:

- `.github/workflows/terraform-cdn.yml`
- `.github/workflows/cdn-sync.yml`
- `.github/workflows/terraform-drift.yml` (job `plan-drift`)

Action compartilhada: `.github/actions/configure-aws-oidc`.

Após validar OIDC em produção, **remover** `AWS_ACCESS_KEY_ID` e
`AWS_SECRET_ACCESS_KEY` dos secrets do repositório.

## AWS — Identity Provider

```bash
# Provider OIDC (uma vez por conta)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

## Trust policy (exemplo)

Substitua `ACCOUNT_ID` e ajuste o `sub` ao repo/branch desejados.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:BennyLopesWeb/coreflow-beautyos:*"
        }
      }
    }
  ]
}
```

## Permissões da role

Mínimo recomendado para CDN/Terraform deste repo:

- S3 do bucket de state + bucket CDN
- DynamoDB da tabela de locks Terraform
- CloudFront invalidation (se o sync CDN invalidar)
- Demais ações já usadas pelos modules `infra/terraform`

## Validação

1. Configurar `AWS_ROLE_ARN` + `AWS_REGION` no GitHub
2. `workflow_dispatch` em **CoreFlow Terraform CDN** com `plan` / env `dev`
3. Confirmar logs: `AssumeRoleWithWebIdentity` sem access keys
4. Remover secrets estáticos
