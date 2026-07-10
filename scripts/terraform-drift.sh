#!/usr/bin/env bash
# Terraform drift detection — config hash + optional plan (CF-22).
set -euo pipefail

ENVIRONMENT="${1:-all}"
MODE="${2:-config}"

ROOT="$(dirname "$0")/.."

cd "$ROOT/backend"
python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.terraform_drift_service import TerraformDriftService
from app.core.config import settings

plugin_registry.load_all()
svc = TerraformDriftService()

env = '$ENVIRONMENT'
mode = '$MODE'

if mode == 'plan':
    if not settings.TERRAFORM_DRIFT_LIVE:
        raise SystemExit('TERRAFORM_DRIFT_LIVE=false')
    result = svc.plan_drift(env)
elif env == 'all':
    result = svc.detect_all_config_drift()
else:
    result = svc.config_drift(env)

import json
print(json.dumps(result, indent=2))

if result.get('has_drift') or result.get('has_any_drift'):
    raise SystemExit(2)
"
