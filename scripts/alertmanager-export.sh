#!/usr/bin/env bash
# Export Alertmanager + Prometheus alerting rules (CF-24).
set -euo pipefail

ROOT="$(dirname "$0")/.."

cd "$ROOT/backend"
python -c "
from app.modules.observability.application.alertmanager_rules_service import AlertmanagerRulesService
print(AlertmanagerRulesService().export_all())
"
