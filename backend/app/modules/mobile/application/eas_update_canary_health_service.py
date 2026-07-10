"""
EasUpdateCanaryHealthService — health check de canary OTA por segmento (CF-22).

Avalia taxa de sucesso e amostras mínimas antes de permitir auto-promote
do canal canary para production.
"""
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_service import EasUpdateCanaryService

logger = get_logger("eas_canary_health")

# Store in-memory para modo mock (testes e dev sem probe live)
_CANARY_HEALTH_SAMPLES: Dict[str, Dict[str, int]] = {}


class EasUpdateCanaryHealthService:
    """
    Coleta e avalia saúde de deployments canary EAS Update por segmento.

    Modo live faz probe HTTP no endpoint configurado no manifest.
    Modo mock usa amostras registradas via API ou defaults otimistas.
    """

    def __init__(self, canary_service: Optional[EasUpdateCanaryService] = None):
        """
        Args:
            canary_service: Serviço canary base (opcional para testes).
        """
        self.canary = canary_service or EasUpdateCanaryService()

    @staticmethod
    def sample_key(plugin_id: str, segment: str) -> str:
        """
        Gera chave única plugin + segmento.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento de mercado.

        Returns:
            String ``plugin_id:segment``.
        """
        return f"{plugin_id}:{segment}"

    def health_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve thresholds de health do manifest ou settings globais.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict min_success_rate, min_samples, probe_url, auto_promote.
        """
        manifest = plugin_registry.get(plugin_id)
        mobile_update = (manifest.mobile or {}).get("update", {}) if manifest else {}
        health = mobile_update.get("canary_health", {})
        cdn_host = (manifest.mobile or {}).get("cdn_host", settings.MOBILE_CDN_BASE_URL) if manifest else settings.MOBILE_CDN_BASE_URL
        default_url = f"https://{cdn_host}/health" if "://" not in cdn_host else f"{cdn_host.rstrip('/')}/health"

        return {
            "auto_promote": mobile_update.get(
                "canary_auto_promote", settings.MOBILE_EAS_UPDATE_CANARY_AUTO_PROMOTE
            ),
            "min_success_rate": health.get(
                "min_success_rate", settings.MOBILE_EAS_UPDATE_CANARY_HEALTH_MIN_SUCCESS_RATE
            ),
            "min_samples": health.get(
                "min_samples", settings.MOBILE_EAS_UPDATE_CANARY_HEALTH_MIN_SAMPLES
            ),
            "probe_url": health.get("probe_url", default_url),
        }

    def record_sample(self, plugin_id: str, segment: str, success: bool) -> Dict[str, Any]:
        """
        Registra amostra de health (modo mock ou ingestão externa).

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.
            success: True se requisição/sessão OK.

        Returns:
            Estatísticas atualizadas do segmento.
        """
        key = self.sample_key(plugin_id, segment)
        bucket = _CANARY_HEALTH_SAMPLES.setdefault(key, {"success": 0, "failure": 0})
        if success:
            bucket["success"] += 1
        else:
            bucket["failure"] += 1
        return self._stats_from_bucket(bucket)

    def probe_health(self, plugin_id: str, segment: str) -> Dict[str, Any]:
        """
        Executa probe de health live ou retorna amostras mock.

        Args:
            plugin_id: ID do plugin vertical.
            segment: Segmento canary.

        Returns:
            Dict com healthy, success_rate, samples e probe_mode.

        Raises:
            ValueError: Segmento inválido.
        """
        self.canary.list_segments(plugin_id)
        if segment not in self.canary.list_segments(plugin_id):
            raise ValueError(f"Segmento '{segment}' inválido para {plugin_id}")

        cfg = self.health_config(plugin_id)

        if settings.MOBILE_EAS_UPDATE_CANARY_HEALTH_LIVE:
            live_ok = self._probe_url(cfg["probe_url"])
            stats = {"success": 1 if live_ok else 0, "failure": 0 if live_ok else 1, "total": 1}
            success_rate = 1.0 if live_ok else 0.0
            probe_mode = "live"
        else:
            key = self.sample_key(plugin_id, segment)
            bucket = _CANARY_HEALTH_SAMPLES.get(key, {"success": 0, "failure": 0})
            if bucket["success"] + bucket["failure"] == 0:
                bucket = {"success": int(cfg["min_samples"]), "failure": 0}
            stats = self._stats_from_bucket(bucket)
            success_rate = stats["success_rate"]
            probe_mode = "mock"

        healthy = (
            stats["total"] >= cfg["min_samples"]
            and success_rate >= cfg["min_success_rate"]
        )

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "healthy": healthy,
            "success_rate": success_rate,
            "samples": stats["total"],
            "success_count": stats["success"],
            "failure_count": stats["failure"],
            "min_success_rate": cfg["min_success_rate"],
            "min_samples": cfg["min_samples"],
            "probe_url": cfg["probe_url"],
            "probe_mode": probe_mode,
            "auto_promote_enabled": cfg["auto_promote"],
        }

    def _probe_url(self, url: str) -> bool:
        """
        Faz GET HTTP no endpoint de health.

        Args:
            url: URL completa do probe.

        Returns:
            True se status 2xx.
        """
        try:
            response = httpx.get(url, timeout=5.0, follow_redirects=True)
            return response.status_code < 400
        except Exception as exc:
            logger.warning(f"[canary-health] Probe falhou {url}: {exc}")
            return False

    @staticmethod
    def _stats_from_bucket(bucket: Dict[str, int]) -> Dict[str, Any]:
        """
        Calcula taxa de sucesso a partir de contadores.

        Args:
            bucket: Dict success/failure.

        Returns:
            Dict total, success, failure, success_rate.
        """
        success = bucket.get("success", 0)
        failure = bucket.get("failure", 0)
        total = success + failure
        rate = (success / total) if total else 0.0
        return {
            "success": success,
            "failure": failure,
            "total": total,
            "success_rate": rate,
        }

    @classmethod
    def reset_samples(cls) -> None:
        """
        Limpa amostras mock (útil em testes).

        Returns:
            None
        """
        _CANARY_HEALTH_SAMPLES.clear()
