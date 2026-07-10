#!/usr/bin/env bash
# Export Grafana dashboards as code (CF-23).
set -euo pipefail

ROOT="$(dirname "$0")/.."

cd "$ROOT/backend"
python -c "
from app.modules.observability.application.grafana_dashboard_service import GrafanaDashboardService
print(GrafanaDashboardService().export_all())
"
