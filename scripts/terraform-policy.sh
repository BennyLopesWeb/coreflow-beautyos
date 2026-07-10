#!/usr/bin/env bash
# Terraform OPA policy check (CF-23).
set -euo pipefail

ENVIRONMENT="${1:-all}"

ROOT="$(dirname "$0")/.."

cd "$ROOT/backend"
python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_policy_service import TerraformPolicyService

plugin_registry.load_all()
svc = TerraformPolicyService()

env = '$ENVIRONMENT'
if env == 'all':
    result = svc.evaluate_all()
else:
    result = svc.evaluate(env)

import json
print(json.dumps(result, indent=2))

passed = result.get('all_passed') if env == 'all' else result.get('passed')
if not passed:
    raise SystemExit(1)
"
