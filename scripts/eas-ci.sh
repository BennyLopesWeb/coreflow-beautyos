#!/usr/bin/env bash
# EAS CI helper — build white-label por plugin (CF-16/17).
set -euo pipefail

PROFILE="${1:-preview}"
PLATFORM="${2:-all}"
PLUGIN_ID="${3:-beauty}"

if [[ -z "${EXPO_TOKEN:-}" ]]; then
  echo "❌ EXPO_TOKEN não definido. Exporte: export EXPO_TOKEN=..."
  exit 1
fi

ROOT="$(dirname "$0")/.."
cd "$ROOT/frontend"

echo "📦 npm ci..."
npm ci

echo "🔍 typecheck..."
npm run typecheck

PROFILE_KEY="${PLUGIN_ID}-${PROFILE}"
echo "📱 Plugin: $PLUGIN_ID | Profile key: $PROFILE_KEY"

if [[ -f eas.plugins.json ]]; then
  echo "✅ eas.plugins.json encontrado"
else
  echo "⚙️  Gerando eas.plugins.json via backend..."
  cd "$ROOT/backend"
  python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService
plugin_registry.load_all()
EasWhitelabelService().generate_plugins_file()
"
  cd "$ROOT/frontend"
fi

echo "🚀 eas build --profile $PROFILE_KEY --platform $PLATFORM"
npx eas-cli build --profile "$PROFILE_KEY" --platform "$PLATFORM" --non-interactive --no-wait

echo "✅ Build EAS submetido (plugin=$PLUGIN_ID profile=$PROFILE platform=$PLATFORM)"
