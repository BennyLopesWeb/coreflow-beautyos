"""
AlertmanagerRulesService — regras de alerta DLQ as code (CF-24).

Gera Prometheus alerting rules e config Alertmanager para observabilidade
de dead-letter queue e replay automático.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("alertmanager_rules")

ALERTMANAGER_DIR = Path(__file__).resolve().parents[5] / "infra" / "alertmanager"
PROMETHEUS_RULES_DIR = Path(__file__).resolve().parents[5] / "infra" / "prometheus" / "rules"


class AlertmanagerRulesService:
    """
    Exporta regras Prometheus + rotas Alertmanager para alertas DLQ.

    Regras monitoram ``coreflow_dlq_pending``, ``coreflow_dlq_eligible_now``
    e taxa de falha de replay via ``coreflow_dlq_replay_total``.
    """

    RULE_GROUP_NAME = "coreflow_dlq"
    RULE_FILE_NAME = "coreflow-dlq.yml"

    def __init__(
        self,
        alertmanager_dir: Optional[Path] = None,
        prometheus_rules_dir: Optional[Path] = None,
    ):
        """
        Args:
            alertmanager_dir: Raiz infra/alertmanager/.
            prometheus_rules_dir: Diretório de rules Prometheus.
        """
        self.alertmanager_dir = alertmanager_dir or ALERTMANAGER_DIR
        self.prometheus_rules_dir = prometheus_rules_dir or PROMETHEUS_RULES_DIR

    def prometheus_alert_rules(self) -> Dict[str, Any]:
        """
        Monta documento YAML de alerting rules Prometheus.

        Returns:
            Dict groups/rules compatível com prometheus.yml rule_files.
        """
        pending_threshold = settings.ALERTMANAGER_DLQ_PENDING_THRESHOLD
        eligible_threshold = settings.ALERTMANAGER_DLQ_ELIGIBLE_THRESHOLD
        failure_rate = settings.ALERTMANAGER_DLQ_FAILURE_RATE_THRESHOLD

        return {
            "groups": [
                {
                    "name": self.RULE_GROUP_NAME,
                    "rules": [
                        {
                            "alert": "CoreFlowDLQPendingHigh",
                            "expr": f"coreflow_dlq_pending > {pending_threshold}",
                            "for": "5m",
                            "labels": {
                                "severity": "warning",
                                "component": "dlq",
                                "team": "platform",
                            },
                            "annotations": {
                                "summary": "DLQ com mensagens pendentes elevadas",
                                "description": (
                                    "{{ $value }} mensagens DLQ pendentes de replay "
                                    f"(threshold={pending_threshold})."
                                ),
                                "runbook_url": "https://docs.coreflow.app/runbooks/dlq-pending",
                            },
                        },
                        {
                            "alert": "CoreFlowDLQEligibleHigh",
                            "expr": f"coreflow_dlq_eligible_now > {eligible_threshold}",
                            "for": "2m",
                            "labels": {
                                "severity": "critical",
                                "component": "dlq",
                                "team": "platform",
                            },
                            "annotations": {
                                "summary": "DLQ elegível para replay imediato",
                                "description": (
                                    "{{ $value }} mensagens prontas para replay agora."
                                ),
                            },
                        },
                        {
                            "alert": "CoreFlowDLQReplayFailureRateHigh",
                            "expr": (
                                "sum(rate(coreflow_dlq_replay_total{status=\"failed\"}[5m])) "
                                "/ clamp_min(sum(rate(coreflow_dlq_replay_total[5m])), 0.001) "
                                f"> {failure_rate}"
                            ),
                            "for": "3m",
                            "labels": {
                                "severity": "warning",
                                "component": "dlq-replay",
                            },
                            "annotations": {
                                "summary": "Taxa alta de falhas no replay DLQ",
                                "description": (
                                    "Mais de "
                                    f"{int(failure_rate * 100)}% dos replays falhando nos últimos 5m."
                                ),
                            },
                        },
                        {
                            "alert": "CoreFlowDLQReplayStalled",
                            "expr": (
                                "coreflow_dlq_pending > 0 "
                                "and increase(coreflow_dlq_replay_total{status=\"success\"}[30m]) == 0"
                            ),
                            "for": "10m",
                            "labels": {
                                "severity": "critical",
                                "component": "dlq-replay",
                            },
                            "annotations": {
                                "summary": "Replay DLQ parado com backlog",
                                "description": (
                                    "Há mensagens pendentes mas nenhum replay bem-sucedido em 30m."
                                ),
                            },
                        },
                    ],
                }
            ],
        }

    def alertmanager_config(self) -> Dict[str, Any]:
        """
        Monta config Alertmanager com rotas por severidade.

        Returns:
            Dict config Alertmanager (route + receivers).
        """
        routes = [
            {
                "matchers": ['severity="critical"'],
                "receiver": "coreflow-critical",
                "continue": True,
            },
            {
                "matchers": ['component="dlq"'],
                "receiver": "coreflow-dlq",
                "continue": True,
            },
        ]
        if settings.ALERTMANAGER_PAGERDUTY_ENABLED:
            routes.append(
                {
                    "matchers": ['severity="critical"'],
                    "receiver": "coreflow-pagerduty",
                    "continue": False,
                }
            )
        if settings.ALERTMANAGER_OPSGENIE_ENABLED:
            routes.append(
                {
                    "matchers": ['severity=~"critical|warning"'],
                    "receiver": "coreflow-opsgenie",
                    "continue": False,
                }
            )

        receivers = [
            {
                "name": "coreflow-default",
                "webhook_configs": [
                    {"url": settings.ALERTMANAGER_DEFAULT_WEBHOOK_URL, "send_resolved": True},
                ],
            },
            {
                "name": "coreflow-critical",
                "webhook_configs": [
                    {"url": settings.ALERTMANAGER_CRITICAL_WEBHOOK_URL, "send_resolved": True},
                ],
            },
            {
                "name": "coreflow-dlq",
                "webhook_configs": [
                    {"url": settings.ALERTMANAGER_DLQ_WEBHOOK_URL, "send_resolved": True},
                ],
            },
        ]
        receivers.extend(self._pagerduty_receiver())
        receivers.extend(self._opsgenie_receiver())

        return {
            "global": {
                "resolve_timeout": "5m",
            },
            "route": {
                "receiver": "coreflow-default",
                "group_by": ["alertname", "component"],
                "group_wait": "30s",
                "group_interval": "5m",
                "repeat_interval": "4h",
                "routes": routes,
            },
            "receivers": receivers,
        }

    def _pagerduty_receiver(self) -> List[Dict[str, Any]]:
        """
        Receiver PagerDuty Events API v2 (CF-25).

        Returns:
            Lista com receiver ou vazia se desabilitado.
        """
        if not settings.ALERTMANAGER_PAGERDUTY_ENABLED:
            return []
        return [
            {
                "name": "coreflow-pagerduty",
                "pagerduty_configs": [
                    {
                        "routing_key": settings.ALERTMANAGER_PAGERDUTY_ROUTING_KEY,
                        "severity": "{{ if eq .CommonLabels.severity \"critical\" }}critical{{ else }}warning{{ end }}",
                        "description": "{{ .CommonAnnotations.summary }}",
                        "details": {
                            "component": "{{ .CommonLabels.component }}",
                            "alertname": "{{ .CommonLabels.alertname }}",
                        },
                    }
                ],
            }
        ]

    def _opsgenie_receiver(self) -> List[Dict[str, Any]]:
        """
        Receiver Opsgenie (CF-25).

        Returns:
            Lista com receiver ou vazia se desabilitado.
        """
        if not settings.ALERTMANAGER_OPSGENIE_ENABLED:
            return []
        return [
            {
                "name": "coreflow-opsgenie",
                "opsgenie_configs": [
                    {
                        "api_key": settings.ALERTMANAGER_OPSGENIE_API_KEY,
                        "message": "{{ .CommonAnnotations.summary }}",
                        "description": "{{ .CommonAnnotations.description }}",
                        "priority": "{{ if eq .CommonLabels.severity \"critical\" }}P1{{ else }}P3{{ end }}",
                        "tags": "{{ .CommonLabels.component }},{{ .CommonLabels.alertname }}",
                    }
                ],
            }
        ]

    def export_all(self) -> Dict[str, str]:
        """
        Exporta rules Prometheus + alertmanager.yml para infra/.

        Returns:
            Dict com paths exportados.
        """
        self.prometheus_rules_dir.mkdir(parents=True, exist_ok=True)
        self.alertmanager_dir.mkdir(parents=True, exist_ok=True)

        rules_path = self.prometheus_rules_dir / self.RULE_FILE_NAME
        rules_path.write_text(
            yaml.safe_dump(self.prometheus_alert_rules(), sort_keys=False),
            encoding="utf-8",
        )

        am_path = self.alertmanager_dir / "alertmanager.yml"
        am_path.write_text(
            yaml.safe_dump(self.alertmanager_config(), sort_keys=False),
            encoding="utf-8",
        )

        manifest_path = self.alertmanager_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(self.manifest(), indent=2),
            encoding="utf-8",
        )

        logger.info(f"[alertmanager] Rules exportadas → {rules_path}")
        return {
            "prometheus_rules": str(rules_path),
            "alertmanager_config": str(am_path),
            "manifest": str(manifest_path),
        }

    def manifest(self) -> Dict[str, Any]:
        """
        Preview do manifest de alertas DLQ.

        Returns:
            Dict com contagem de rules, thresholds e paths.
        """
        rules = self.prometheus_alert_rules()["groups"][0]["rules"]
        return {
            "version": settings.APP_VERSION,
            "rule_group": self.RULE_GROUP_NAME,
            "rules_count": len(rules),
            "rule_names": [r["alert"] for r in rules],
            "thresholds": {
                "pending": settings.ALERTMANAGER_DLQ_PENDING_THRESHOLD,
                "eligible": settings.ALERTMANAGER_DLQ_ELIGIBLE_THRESHOLD,
                "failure_rate": settings.ALERTMANAGER_DLQ_FAILURE_RATE_THRESHOLD,
            },
            "pagerduty_enabled": settings.ALERTMANAGER_PAGERDUTY_ENABLED,
            "opsgenie_enabled": settings.ALERTMANAGER_OPSGENIE_ENABLED,
            "export_command": "./scripts/alertmanager-export.sh",
        }
