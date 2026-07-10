#!/usr/bin/env bash
# EAS Submit helper — App Store / Play Store por plugin (CF-18).
set -euo pipefail

PLUGIN_ID="${1:-beauty}"
PLATFORM="${2:-all}"

if [[ -z "${EXPO_TOKEN:-}" ]]; then
  echo "❌ EXPO_TOKEN não definido. Exporte: export EXPO_TOKEN=..."
  exit 1
fi

ROOT="$(dirname "$0")/.."
cd "$ROOT/frontend"

echo "📦 npm ci..."
npm ci

if [[ ! -f eas.submit.json ]]; then
  echo "⚙️  Gerando eas.submit.json via backend..."
  cd "$ROOT/backend"
  python -c "
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_submit_service import EasSubmitService
plugin_registry.load_all()
EasSubmitService().generate_submit_file()
"
  cd "$ROOT/frontend"
fi

SUBMIT_KEY="${PLUGIN_ID}-production"
echo "📤 eas submit --profile $SUBMIT_KEY --platform $PLATFORM --latest"
npx eas-cli submit --profile "$SUBMIT_KEY" --platform "$PLATFORM" --non-interactive --latest

echo "✅ Submit EAS concluído (plugin=$PLUGIN_ID platform=$PLATFORM)"
