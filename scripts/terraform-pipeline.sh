#!/usr/bin/env bash
# Terraform multi-environment pipeline dev → staging → prod (CF-21).
set -euo pipefail

ACTION="${1:-plan-all}"
ENVIRONMENT="${2:-dev}"

ROOT="$(dirname "$0")/.."
CDN_SCRIPT="$ROOT/scripts/terraform-cdn.sh"

export_all() {
  echo "📦 Exportando pipeline multi-ambiente..."
  cd "$ROOT/backend"
  python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_pipeline_service import TerraformPipelineService
plugin_registry.load_all()
svc = TerraformPipelineService()
print(svc.export_all_environments())
print(svc.export_pipeline_manifest())
"
}

case "$ACTION" in
  export)
    export_all
    ;;
  plan-all)
    export_all
    for env in dev staging prod; do
      echo "🔍 Plan $env..."
      "$CDN_SCRIPT" "$env" plan
    done
    ;;
  apply-all)
    export_all
    for env in dev staging prod; do
      echo "🚀 Apply $env..."
      "$CDN_SCRIPT" "$env" apply
    done
    ;;
  plan|apply)
    export_all
    "$CDN_SCRIPT" "$ENVIRONMENT" "$ACTION"
    ;;
  *)
    echo "Uso: $0 {export|plan-all|apply-all|plan|apply} [environment]"
    exit 1
    ;;
esac
