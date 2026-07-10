"""
ReadinessScoreService — Core Readiness Score (R1-F2).

Indicadores de maturidade arquitetural para priorização de releases.
"""
from typing import Any, Dict, List

from app.core.architecture_metrics import ArchitectureMetricsStore, test_coverage_by_module


class ReadinessScoreService:
    """
    Calcula painel de prontidão da plataforma CoreFlow.

    Percentuais baseados em auditoria ArchitectureAssessment (jul/2026)
    ajustados por sinais runtime quando disponíveis.
    """

    BASE_SCORES: Dict[str, int] = {
        "hexagonal": 35,
        "ddd": 40,
        "plugin_architecture": 55,
        "resource_engine": 15,
        "scheduling_engine": 20,
        "ai_platform": 10,
        "workflow_engine": 25,
        "marketplace": 0,
        "api_first": 45,
        "event_driven": 55,
        "observability": 50,
    }

    def scoreboard(self) -> Dict[str, Any]:
        """
        Retorna scoreboard completo com items e média.

        Returns:
            Dict items[], average, methodology.
        """
        metrics = ArchitectureMetricsStore.get().snapshot()
        items = self._build_items(metrics)
        average = round(sum(i["score"] for i in items) / len(items), 1) if items else 0
        return {
            "methodology": "ArchitectureAssessment + runtime HTTP migration %",
            "average": average,
            "items": items,
        }

    def _build_items(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Monta lista de itens com score e status.

        Args:
            metrics: Snapshot architecture metrics.

        Returns:
            Lista de dicts name, score, status.
        """
        api_first_boost = min(15, int(metrics["http"].get("core_percentage", 0) / 5))
        items = []
        for key, base in self.BASE_SCORES.items():
            score = base
            if key == "api_first":
                score = min(100, base + api_first_boost)
            status = self._status_label(score)
            items.append(
                {
                    "name": key,
                    "label": self._label(key),
                    "score": score,
                    "status": status,
                }
            )
        return items

    @staticmethod
    def _label(key: str) -> str:
        """
        Rótulo legível para chave interna.

        Args:
            key: Identificador snake_case.

        Returns:
            Label formatado.
        """
        labels = {
            "hexagonal": "Hexagonal",
            "ddd": "DDD",
            "plugin_architecture": "Plugin Architecture",
            "resource_engine": "Resource Engine",
            "scheduling_engine": "Scheduling Engine",
            "ai_platform": "AI Platform",
            "workflow_engine": "Workflow Engine",
            "marketplace": "Marketplace",
            "api_first": "API First",
            "event_driven": "Event Driven",
            "observability": "Observability",
        }
        return labels.get(key, key)

    @staticmethod
    def _status_label(score: int) -> str:
        """
        Classifica score em faixa.

        Args:
            score: Percentual 0–100.

        Returns:
            critical | emerging | maturing | strong.
        """
        if score >= 70:
            return "strong"
        if score >= 40:
            return "maturing"
        if score >= 15:
            return "emerging"
        return "critical"

    def coverage_summary(self) -> Dict[str, Any]:
        """
        Resumo cobertura de testes por módulo.

        Returns:
            Dict de test_coverage_by_module().
        """
        return test_coverage_by_module()
