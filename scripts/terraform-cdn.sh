#!/usr/bin/env bash
# Terraform CDN apply helper (CF-20).
set -euo pipefail

ENVIRONMENT="${1:-dev}"
ACTION="${2:-plan}"

ROOT="$(dirname "$0")/.."
TF_DIR="$ROOT/infra/terraform/environments/$ENVIRONMENT"

echo "⚙️  Exportando tfvars + backend..."
cd "$ROOT/backend"
python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
plugin_registry.load_all()
svc = TerraformPipelineService()
print(svc.export_environment('$ENVIRONMENT'))
"

cd "$TF_DIR"
terraform init -backend-config=backend.hcl

if [[ "$ACTION" == "apply" ]]; then
  terraform apply -var-file=terraform.tfvars.json -auto-approve
else
  terraform plan -var-file=terraform.tfvars.json
fi
