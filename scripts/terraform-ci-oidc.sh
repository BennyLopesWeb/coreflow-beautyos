#!/usr/bin/env bash
# Aplica/planeja o stack CI OIDC (R4-F17).
# Uso: ./scripts/terraform-ci-oidc.sh [plan|apply]
set -euo pipefail

ACTION="${1:-plan}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="$ROOT/infra/terraform/environments/ci-oidc"

cd "$ENV_DIR"
terraform init -backend-config=backend.hcl -input=false
case "$ACTION" in
  plan)
    terraform plan -var-file=terraform.tfvars.json
    ;;
  apply)
    terraform apply -var-file=terraform.tfvars.json -auto-approve
    echo ""
    echo "Configure no GitHub:"
    echo "  Secret AWS_ROLE_ARN = $(terraform output -raw aws_role_arn)"
    echo "  Variable AWS_REGION = us-east-1"
    ;;
  *)
    echo "Uso: $0 [plan|apply]" >&2
    exit 1
    ;;
esac
