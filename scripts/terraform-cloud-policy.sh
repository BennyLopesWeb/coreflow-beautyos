#!/usr/bin/env bash
# Export Terraform Cloud policy set (CF-25).
set -euo pipefail

ROOT="$(dirname "$0")/.."

cd "$ROOT/backend"
python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_cloud_policy_service import TerraformCloudPolicyService

plugin_registry.load_all()
svc = TerraformCloudPolicyService()
print(svc.export_policy_set())
result = svc.evaluate_all()
print('validation:', result)
import sys
sys.exit(0 if result.get('all_passed') else 1)
"
