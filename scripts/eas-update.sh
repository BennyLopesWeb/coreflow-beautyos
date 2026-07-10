#!/usr/bin/env bash
# EAS Update OTA helper — canal por plugin (CF-19).
set -euo pipefail

PLUGIN_ID="${1:-beauty}"
ENVIRONMENT="${2:-preview}"
MESSAGE="${3:-OTA update CoreFlow}"

if [[ -z "${EXPO_TOKEN:-}" ]]; then
  echo "❌ EXPO_TOKEN não definido. Exporte: export EXPO_TOKEN=..."
  exit 1
fi

ROOT="$(dirname "$0")/.."
cd "$ROOT/frontend"

echo "📦 npm ci..."
npm ci

if [[ ! -f eas.update.json ]]; then
  echo "⚙️  Gerando eas.update.json via backend..."
  cd "$ROOT/backend"
  python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_service import EasUpdateService
plugin_registry.load_all()
EasUpdateService().generate_update_file()
"
  cd "$ROOT/frontend"
fi

UPDATE_KEY="${PLUGIN_ID}-${ENVIRONMENT}"
echo "📡 OTA plugin=$PLUGIN_ID environment=$ENVIRONMENT key=$UPDATE_KEY"

BRANCH=$(python -c "import json; d=json.load(open('eas.update.json')); print(d['update']['$UPDATE_KEY']['branch'])")
CHANNEL=$(python -c "import json; d=json.load(open('eas.update.json')); print(d['update']['$UPDATE_KEY']['channel'])")

echo "🚀 eas update --branch $BRANCH --channel $CHANNEL"
npx eas-cli update --branch "$BRANCH" --channel "$CHANNEL" --message "$MESSAGE" --non-interactive

echo "✅ EAS Update publicado (plugin=$PLUGIN_ID env=$ENVIRONMENT)"
