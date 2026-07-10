"""
EasUpdateCanaryService — OTA canary por segmento de usuário (CF-21).

Usa ``segments`` do manifest do plugin para canais EAS Update dedicados,
permitindo rollout isolado por vertical (ex.: trancista, futebol).
"""
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_service import EasUpdateService

logger = get_logger("eas_update_canary")


class EasUpdateCanaryService:
    """
    Gera planos e comandos EAS Update canary por segmento de mercado.

    Cada segmento recebe channel/branch dedicados:
    ``{plugin_id}-canary-{segment}`` com rollout percentual configurável.
    """

    def __init__(self, update_service: Optional[EasUpdateService] = None):
        """
        Args:
            update_service: Serviço base EAS Update (opcional para testes).
        """
        self.updates = update_service or EasUpdateService()

    def list_segments(self, plugin_id: str) -> List[str]:
        """
        Lista segmentos canary disponíveis para um plugin.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Lista de segment ids (ex.: trancista, futebol).
        """
        manifest = plugin_registry.get(plugin_id)
        if not manifest:
            return []
        mobile = manifest.mobile or {}
        canary = mobile.get("update", {}).get("canary_segments")
        if canary:
            return list(canary)
        return list(manifest.segments or [])

    def canary_channel(self, plugin_id: str, segment: str) -> str:
        """
        Resolve nome do channel canary para plugin + segmento.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento de mercado.

        Returns:
            Nome do channel EAS (ex.: beauty-canary-trancista).
        """
        safe_segment = segment.replace(" ", "-").lower()
        return f"{plugin_id}-canary-{safe_segment}"

    def build_canary_plan(
        self,
        plugin_id: str,
        segment: str,
        percentage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Monta plano canary OTA para um segmento específico.

        Args:
            plugin_id: ID do plugin vertical.
            segment: Segmento alvo (deve existir no manifest).
            percentage: Percentual canary ou default do manifest.

        Returns:
            Dict com channel, branch, env vars e comando eas update.

        Raises:
            ValueError: Segmento inválido para o plugin.
        """
        segments = self.list_segments(plugin_id)
        if segment not in segments:
            raise ValueError(
                f"Segmento '{segment}' inválido para {plugin_id}. "
                f"Válidos: {segments}"
            )

        manifest = plugin_registry.get(plugin_id)
        mobile_update = (manifest.mobile or {}).get("update", {}) if manifest else {}
        pct = percentage if percentage is not None else mobile_update.get(
            "canary_percentage", settings.MOBILE_EAS_UPDATE_CANARY_DEFAULT_PCT
        )
        channel = self.canary_channel(plugin_id, segment)
        branch = mobile_update.get("canary_branch", channel)
        cfg = self.updates.update_config(plugin_id)

        env = {
            "EXPO_PUBLIC_CANARY_SEGMENT": segment,
            "EXPO_PUBLIC_CANARY_ENABLED": "true",
            "EXPO_PUBLIC_PLUGIN_ID": plugin_id,
        }
        cmd = (
            f"eas update --branch {branch} --channel {channel} "
            f"--message \"Canary {segment} {pct}%\" --non-interactive"
        )
        if pct < 100:
            cmd += f" --rollout-percentage {pct}"

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "canary_channel": channel,
            "canary_branch": branch,
            "rollout_percentage": pct,
            "runtime_version": cfg["runtime_version"],
            "env": env,
            "command": cmd,
            "available_segments": segments,
        }

    def list_canary_plans(self, plugin_id: str) -> List[Dict[str, Any]]:
        """
        Lista planos canary para todos os segmentos de um plugin.

        Args:
            plugin_id: ID do plugin.

        Returns:
            Lista de planos canary por segmento.
        """
        return [self.build_canary_plan(plugin_id, seg) for seg in self.list_segments(plugin_id)]
