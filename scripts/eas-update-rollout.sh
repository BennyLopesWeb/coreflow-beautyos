#!/usr/bin/env bash
# EAS Update rollout gradual por plugin (CF-20).
set -euo pipefail

PLUGIN_ID="${1:-beauty}"
ENVIRONMENT="${2:-production}"
TARGET_PCT="${3:-50}"
MESSAGE="${4:-Rollout OTA CoreFlow}"

if [[ -z "${EXPO_TOKEN:-}" ]]; then
  echo "❌ EXPO_TOKEN não definido."
  exit 1
fi

ROOT="$(dirname "$0")/.."
cd "$ROOT/backend"

CMD=$(python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_service import EasUpdateService
plugin_registry.load_all()
print(EasUpdateService().update_command(
    '$PLUGIN_ID', '$ENVIRONMENT', '$MESSAGE', rollout_percentage=int('$TARGET_PCT')
))
")

cd "$ROOT/frontend"
echo "🚀 $CMD"
eval "npx eas-cli $CMD"
echo "✅ Rollout ${TARGET_PCT}% publicado (plugin=$PLUGIN_ID)"
