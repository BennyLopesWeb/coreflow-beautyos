"""
EasUpdateCanaryPromoteService — auto-promote canary → production (CF-22).

Promove branch canary para channel production quando health check passa.
"""
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_rollback_service import EasUpdateCanaryRollbackService
from app.modules.mobile.application.eas_update_canary_service import EasUpdateCanaryService
from app.modules.mobile.application.eas_update_service import EasUpdateService

logger = get_logger("eas_canary_promote")


class EasUpdateCanaryPromoteService:
    """
    Avalia health canary e gera plano de promoção para channel production.

    Auto-promote só ocorre quando ``canary_auto_promote`` está habilitado
    no manifest e o health check atinge thresholds configurados.
    """

    def __init__(
        self,
        canary_service: Optional[EasUpdateCanaryService] = None,
        health_service: Optional[EasUpdateCanaryHealthService] = None,
        update_service: Optional[EasUpdateService] = None,
    ):
        """
        Args:
            canary_service: Serviço canary base.
            health_service: Serviço de health check.
            update_service: Serviço EAS Update.
        """
        self.canary = canary_service or EasUpdateCanaryService()
        self.health = health_service or EasUpdateCanaryHealthService(self.canary)
        self.updates = update_service or EasUpdateService()

    def evaluate(self, plugin_id: str, segment: str) -> Dict[str, Any]:
        """
        Avalia se canary está pronto para promoção.

        Args:
            plugin_id: ID do plugin vertical.
            segment: Segmento canary.

        Returns:
            Dict decision (promote|hold), health e motivo.

        Raises:
            ValueError: Segmento inválido.
        """
        health = self.health.probe_health(plugin_id, segment)
        canary_plan = self.canary.build_canary_plan(plugin_id, segment)

        if not settings.MOBILE_EAS_UPDATE_CANARY_ENABLED:
            return self._hold(plugin_id, segment, health, canary_plan, "canary_disabled")

        if not health["auto_promote_enabled"]:
            return self._hold(plugin_id, segment, health, canary_plan, "auto_promote_disabled")

        if not health["healthy"]:
            reason = "insufficient_samples" if health["samples"] < health["min_samples"] else "low_success_rate"
            return self._hold(plugin_id, segment, health, canary_plan, reason)

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "decision": "promote",
            "reason": "health_check_passed",
            "health": health,
            "canary": canary_plan,
            "promote_plan": self.build_promote_plan(plugin_id, segment),
        }

    def build_promote_plan(self, plugin_id: str, segment: str) -> Dict[str, Any]:
        """
        Monta comando EAS para promover canary branch ao channel production.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            Dict com channels, branch e comando eas channel:edit.

        Raises:
            ValueError: Segmento inválido.
        """
        canary_plan = self.canary.build_canary_plan(plugin_id, segment)
        cfg = self.updates.update_config(plugin_id)
        production_channel = cfg["production_channel"]
        canary_branch = canary_plan["canary_branch"]

        cmd = (
            f"eas channel:edit {production_channel} --branch {canary_branch} "
            f"--non-interactive"
        )
        update_cmd = (
            f"eas update --branch {canary_branch} --channel {production_channel} "
            f"--message \"Promote canary {segment} to production\" --non-interactive"
        )

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "from_canary_channel": canary_plan["canary_channel"],
            "to_production_channel": production_channel,
            "branch": canary_branch,
            "command": cmd,
            "update_command": update_cmd,
            "runtime_version": cfg["runtime_version"],
        }

    def auto_promote(self, plugin_id: str, segment: str, force: bool = False) -> Dict[str, Any]:
        """
        Executa auto-promote se health OK (ou force=true).

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.
            force: Ignorar health check (admin).

        Returns:
            Dict com decision e promote_plan se aplicável.

        Raises:
            ValueError: Segmento inválido ou health reprovado sem force.
        """
        evaluation = self.evaluate(plugin_id, segment)

        if force:
            evaluation["decision"] = "promote"
            evaluation["reason"] = "forced"
            evaluation["promote_plan"] = self.build_promote_plan(plugin_id, segment)

        if evaluation["decision"] != "promote":
            if force:
                pass
            else:
                raise ValueError(
                    f"Canary não elegível para promote: {evaluation['reason']}"
                )

        logger.info(
            f"[canary-promote] {plugin_id}/{segment} → {evaluation['promote_plan']['to_production_channel']}"
        )
        cfg = self.updates.update_config(plugin_id)
        EasUpdateCanaryRollbackService().record_promotion(
            plugin_id,
            segment,
            previous_branch=cfg.get("production_branch", cfg["production_channel"]),
        )
        return evaluation

    @staticmethod
    def _hold(
        plugin_id: str,
        segment: str,
        health: Dict[str, Any],
        canary_plan: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """
        Monta resposta de hold (sem promoção).

        Args:
            plugin_id: ID do plugin.
            segment: Segmento.
            health: Resultado do health probe.
            canary_plan: Plano canary atual.
            reason: Motivo do hold.

        Returns:
            Dict com decision=hold.
        """
        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "decision": "hold",
            "reason": reason,
            "health": health,
            "canary": canary_plan,
        }
