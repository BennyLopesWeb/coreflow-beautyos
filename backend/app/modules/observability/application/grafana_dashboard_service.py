"""
GrafanaDashboardService — dashboards as code para métricas DLQ (CF-23).

Gera JSON de dashboard Grafana e arquivos de provisioning para import
automático via sidecar ou API Grafana.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("grafana_dashboard")

GRAFANA_DIR = Path(__file__).resolve().parents[5] / "infra" / "grafana"


class GrafanaDashboardService:
    """
    Monta e exporta dashboards Grafana para observabilidade DLQ CoreFlow.

    Panels usam métricas Prometheus expostas em ``/metrics`` (CF-22):
    ``coreflow_dlq_replay_total``, ``coreflow_dlq_pending``,
    ``coreflow_dlq_eligible_now``, ``coreflow_dlq_replay_duration_seconds``.
    """

    DASHBOARD_UID = "coreflow-dlq"
    DASHBOARD_TITLE = "CoreFlow — DLQ Replay"

    def __init__(self, grafana_dir: Optional[Path] = None):
        """
        Args:
            grafana_dir: Raiz infra/grafana (dashboards + provisioning).
        """
        self.grafana_dir = grafana_dir or GRAFANA_DIR

    def prometheus_datasource(self) -> Dict[str, Any]:
        """
        Configuração de datasource Prometheus para provisioning.

        Returns:
            Dict compatível com Grafana provisioning API.
        """
        return {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": settings.GRAFANA_PROMETHEUS_DATASOURCE,
                    "type": "prometheus",
                    "access": "proxy",
                    "url": settings.GRAFANA_PROMETHEUS_URL,
                    "isDefault": True,
                    "editable": False,
                    "jsonData": {"timeInterval": "15s"},
                }
            ],
        }

    def dashboard_provider(self) -> Dict[str, Any]:
        """
        Provider de dashboards file-based para Grafana sidecar.

        Returns:
            Dict apiVersion 1 provider apontando para /etc/grafana/dashboards.
        """
        return {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "CoreFlow",
                    "orgId": 1,
                    "folder": "CoreFlow Platform",
                    "type": "file",
                    "disableDeletion": False,
                    "updateIntervalSeconds": 30,
                    "allowUiUpdates": True,
                    "options": {"path": "/etc/grafana/dashboards"},
                }
            ],
        }

    def dlq_dashboard_document(self) -> Dict[str, Any]:
        """
        Monta documento JSON completo do dashboard DLQ.

        Returns:
            Dict dashboard Grafana 9+ com panels e queries PromQL.
        """
        ds = {"type": "prometheus", "uid": settings.GRAFANA_PROMETHEUS_DATASOURCE}

        return {
            "uid": self.DASHBOARD_UID,
            "title": self.DASHBOARD_TITLE,
            "tags": ["coreflow", "dlq", "kafka", settings.APP_VERSION],
            "timezone": "browser",
            "schemaVersion": 39,
            "version": 1,
            "refresh": "30s",
            "time": {"from": "now-6h", "to": "now"},
            "panels": self._dlq_panels(ds),
        }

    def _dlq_panels(self, ds: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Lista panels do dashboard DLQ.

        Args:
            ds: Referência datasource Prometheus.

        Returns:
            Lista de panel dicts Grafana.
        """
        return [
            self._stat_panel(
                id=1, title="DLQ Pending", x=0, y=0, w=6, h=4,
                expr="coreflow_dlq_pending", ds=ds,
            ),
            self._stat_panel(
                id=2, title="DLQ Eligible Now", x=6, y=0, w=6, h=4,
                expr="coreflow_dlq_eligible_now", ds=ds,
            ),
            self._timeseries_panel(
                id=3, title="Replay Rate by Status", x=0, y=4, w=12, h=8,
                expr='sum by (status) (rate(coreflow_dlq_replay_total[5m]))',
                ds=ds, legend="{{status}}",
            ),
            self._timeseries_panel(
                id=4, title="Replay Rate by Mode", x=12, y=4, w=12, h=8,
                expr='sum by (mode) (rate(coreflow_dlq_replay_total[5m]))',
                ds=ds, legend="{{mode}}",
            ),
            self._heatmap_panel(
                id=5, title="Replay Duration (p95)", x=0, y=12, w=24, h=8,
                expr=(
                    "histogram_quantile(0.95, "
                    "sum by (le, mode) (rate(coreflow_dlq_replay_duration_seconds_bucket[5m])))"
                ),
                ds=ds,
            ),
        ]

    @staticmethod
    def _stat_panel(
        id: int, title: str, x: int, y: int, w: int, h: int,
        expr: str, ds: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Panel stat (valor instantâneo).

        Args:
            id: ID do panel.
            title: Título exibido.
            x, y, w, h: Grid layout Grafana.
            expr: Query PromQL.
            ds: Datasource ref.

        Returns:
            Dict panel Grafana type stat.
        """
        return {
            "id": id,
            "title": title,
            "type": "stat",
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "datasource": ds,
            "targets": [{"expr": expr, "refId": "A"}],
            "fieldConfig": {"defaults": {"unit": "short"}},
        }

    @staticmethod
    def _timeseries_panel(
        id: int, title: str, x: int, y: int, w: int, h: int,
        expr: str, ds: Dict[str, str], legend: str,
    ) -> Dict[str, Any]:
        """
        Panel timeseries com legenda.

        Args:
            id: ID do panel.
            title: Título.
            x, y, w, h: Grid layout.
            expr: PromQL.
            ds: Datasource.
            legend: Template legenda.

        Returns:
            Dict panel timeseries.
        """
        return {
            "id": id,
            "title": title,
            "type": "timeseries",
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "datasource": ds,
            "targets": [{"expr": expr, "refId": "A", "legendFormat": legend}],
        }

    @staticmethod
    def _heatmap_panel(
        id: int, title: str, x: int, y: int, w: int, h: int,
        expr: str, ds: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Panel timeseries para histograma p95 (simplificado).

        Args:
            id: ID do panel.
            title: Título.
            x, y, w, h: Grid layout.
            expr: PromQL histogram_quantile.
            ds: Datasource.

        Returns:
            Dict panel timeseries.
        """
        return {
            "id": id,
            "title": title,
            "type": "timeseries",
            "gridPos": {"x": x, "y": y, "w": w, "h": h},
            "datasource": ds,
            "targets": [{"expr": expr, "refId": "A", "legendFormat": "{{mode}}"}],
            "fieldConfig": {"defaults": {"unit": "s"}},
        }

    def export_all(self) -> Dict[str, str]:
        """
        Exporta dashboard + provisioning para infra/grafana/.

        Returns:
            Dict com paths exportados.
        """
        dashboards_dir = self.grafana_dir / "dashboards"
        provisioning_dir = self.grafana_dir / "provisioning"
        ds_dir = provisioning_dir / "datasources"
        db_dir = provisioning_dir / "dashboards"

        for directory in (dashboards_dir, ds_dir, db_dir):
            directory.mkdir(parents=True, exist_ok=True)

        dashboard_path = dashboards_dir / "coreflow-dlq.json"
        dashboard_path.write_text(
            json.dumps(self.dlq_dashboard_document(), indent=2),
            encoding="utf-8",
        )

        ds_path = ds_dir / "prometheus.yaml"
        ds_path.write_text(
            json.dumps(self.prometheus_datasource(), indent=2),
            encoding="utf-8",
        )

        provider_path = db_dir / "coreflow.yaml"
        provider_path.write_text(
            json.dumps(self.dashboard_provider(), indent=2),
            encoding="utf-8",
        )

        logger.info(f"[grafana] Dashboard exportado → {dashboard_path}")
        return {
            "dashboard": str(dashboard_path),
            "datasource_provisioning": str(ds_path),
            "dashboard_provisioning": str(provider_path),
        }

    def manifest(self) -> Dict[str, Any]:
        """
        Preview do manifest Grafana as code (sem gravar disco).

        Returns:
            Dict com uid, panels count e paths sugeridos.
        """
        doc = self.dlq_dashboard_document()
        return {
            "version": settings.APP_VERSION,
            "dashboard_uid": self.DASHBOARD_UID,
            "title": self.DASHBOARD_TITLE,
            "panels": len(doc.get("panels", [])),
            "prometheus_url": settings.GRAFANA_PROMETHEUS_URL,
            "export_command": "./scripts/grafana-export.sh",
        }
