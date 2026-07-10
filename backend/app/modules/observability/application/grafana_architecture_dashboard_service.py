"""
GrafanaArchitectureDashboardService — dashboards por camada API (R1-F2).

Panels: Core, Legacy, BeautyOS, Identity, Plugins, Architecture metrics.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.observability.application.grafana_dashboard_service import (
    GRAFANA_DIR,
    GrafanaDashboardService,
)

logger = get_logger("grafana_architecture")

LAYER_DASHBOARD_UID = "coreflow-api-layers"
LAYER_DASHBOARD_TITLE = "CoreFlow — API Layers & Architecture"


class GrafanaArchitectureDashboardService:
    """
    Exporta dashboard Grafana para métricas HTTP por camada e migração legado→core.
    """

    def __init__(self, grafana_dir: Optional[Path] = None):
        """
        Args:
            grafana_dir: Diretório infra/grafana.
        """
        self.grafana_dir = grafana_dir or GRAFANA_DIR
        self._base = GrafanaDashboardService(grafana_dir=self.grafana_dir)

    def layer_dashboard_document(self) -> Dict[str, Any]:
        """
        Monta documento JSON do dashboard API layers.

        Returns:
            Dict dashboard Grafana v38+.
        """
        ds = settings.GRAFANA_PROMETHEUS_DATASOURCE
        panels: List[Dict[str, Any]] = [
            self._stat_panel(1, 0, "Legacy %", f'100 * sum(rate(coreflow_http_requests_total{{layer=~"legacy|beautyos"}}[5m])) / sum(rate(coreflow_http_requests_total[5m]))', ds),
            self._stat_panel(1, 6, "Core %", f'100 * sum(rate(coreflow_http_requests_total{{layer="core"}}[5m])) / sum(rate(coreflow_http_requests_total[5m]))', ds),
            self._timeseries(2, 0, "Requests by Layer", 'sum by (layer) (rate(coreflow_http_requests_total[5m]))', ds, 12, 6),
            self._timeseries(3, 0, "Latency by Layer (p95)", 'histogram_quantile(0.95, sum by (layer, le) (rate(coreflow_http_request_duration_seconds_bucket[5m])))', ds, 12, 6),
            self._timeseries(4, 0, "Errors by Layer", 'sum by (layer, status_class) (rate(coreflow_http_requests_total{{status_class=~"4xx|5xx"}}[5m]))', ds, 12, 6),
            self._timeseries(5, 0, "Identity vs Platform", 'sum by (layer) (rate(coreflow_http_requests_total{{layer=~"identity|platform"}}[5m]))', ds, 12, 6),
        ]
        return {
            "uid": LAYER_DASHBOARD_UID,
            "title": LAYER_DASHBOARD_TITLE,
            "tags": ["coreflow", "architecture", "migration"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "30s",
            "panels": panels,
        }

    @staticmethod
    def _stat_panel(row: int, col: int, title: str, expr: str, datasource: str) -> Dict[str, Any]:
        """
        Panel stat Grafana.

        Args:
            row: Grid row.
            col: Grid col.
            title: Título.
            expr: PromQL.
            datasource: Nome datasource.

        Returns:
            Dict panel.
        """
        return {
            "type": "stat",
            "title": title,
            "gridPos": {"h": 4, "w": 6, "x": col, "y": row},
            "datasource": {"type": "prometheus", "uid": datasource},
            "targets": [{"expr": expr, "refId": "A"}],
        }

    @staticmethod
    def _timeseries(
        row: int,
        col: int,
        title: str,
        expr: str,
        datasource: str,
        width: int,
        height: int,
    ) -> Dict[str, Any]:
        """
        Panel timeseries Grafana.

        Args:
            row: Grid row.
            col: Grid col.
            title: Título.
            expr: PromQL.
            datasource: Datasource.
            width: Largura grid.
            height: Altura grid.

        Returns:
            Dict panel.
        """
        return {
            "type": "timeseries",
            "title": title,
            "gridPos": {"h": height, "w": width, "x": col, "y": row},
            "datasource": {"type": "prometheus", "uid": datasource},
            "targets": [{"expr": expr, "refId": "A"}],
        }

    def export_layer_dashboard(self) -> Dict[str, str]:
        """
        Grava dashboard JSON em infra/grafana/dashboards/.

        Returns:
            Dict path → descrição.
        """
        self.grafana_dir.mkdir(parents=True, exist_ok=True)
        dash_dir = self.grafana_dir / "dashboards"
        dash_dir.mkdir(parents=True, exist_ok=True)
        path = dash_dir / "coreflow-api-layers.json"
        doc = self.layer_dashboard_document()
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        logger.info(f"Dashboard exportado: {path}")
        return {"dashboard": str(path)}

    def export_all(self) -> Dict[str, str]:
        """
        Exporta provisioning + dashboards DLQ e layers.

        Returns:
            Dict paths exportados.
        """
        paths = self._base.export_all()
        paths.update(self.export_layer_dashboard())
        return paths
