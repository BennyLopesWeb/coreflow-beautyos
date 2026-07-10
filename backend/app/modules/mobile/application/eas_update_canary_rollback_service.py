"""
EasUpdateCanaryRollbackService — rollback automático canary (CF-23/25).

Reverte channel production para branch anterior quando health degrada
após promoção canary bem-sucedida. Estado persistido em DB (CF-25).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_update_canary_health_service import EasUpdateCanaryHealthService
from app.modules.mobile.application.eas_update_canary_service import EasUpdateCanaryService
from app.modules.mobile.application.eas_update_service import EasUpdateService
from app.modules.mobile.infrastructure.canary_promotion_repository import CanaryPromotionRepository

logger = get_logger("eas_canary_rollback")


class EasUpdateCanaryRollbackService:
    """
    Detecta degradação pós-promote e gera plano de rollback EAS Update.

    Após ``auto_promote``, o branch production anterior é registrado
    (memória ou ``core_canary_promotions``). Se ``success_rate`` cair
    abaixo de ``rollback_threshold``, rollback restaura production.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        canary_service: Optional[EasUpdateCanaryService] = None,
        health_service: Optional[EasUpdateCanaryHealthService] = None,
        update_service: Optional[EasUpdateService] = None,
        store: Optional[CanaryPromotionRepository] = None,
    ):
        """
        Args:
            db: Sessão SQLAlchemy opcional para persistência.
            canary_service: Serviço canary base.
            health_service: Serviço health probe.
            update_service: Serviço EAS Update.
            store: Repositório de promoções (opcional para testes).
        """
        self.db = db
        self.canary = canary_service or EasUpdateCanaryService()
        self.health = health_service or EasUpdateCanaryHealthService(self.canary)
        self.updates = update_service or EasUpdateService()
        self.store = store or CanaryPromotionRepository(db)

    @staticmethod
    def state_key(plugin_id: str, segment: str) -> str:
        """
        Chave única para estado de promoção.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            String ``plugin_id:segment``.
        """
        return CanaryPromotionRepository.state_key(plugin_id, segment)

    def rollback_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve thresholds de rollback do manifest ou settings.

        Args:
            plugin_id: ID do plugin vertical.

        Returns:
            Dict auto_rollback, rollback_threshold, rollback_min_samples.
        """
        manifest = plugin_registry.get(plugin_id)
        mobile_update = (manifest.mobile or {}).get("update", {}) if manifest else {}
        health = mobile_update.get("canary_health", {})

        return {
            "auto_rollback": mobile_update.get(
                "canary_auto_rollback", settings.MOBILE_EAS_UPDATE_CANARY_AUTO_ROLLBACK
            ),
            "rollback_threshold": health.get(
                "rollback_threshold", settings.MOBILE_EAS_UPDATE_CANARY_ROLLBACK_THRESHOLD
            ),
            "rollback_min_samples": health.get(
                "rollback_min_samples", settings.MOBILE_EAS_UPDATE_CANARY_ROLLBACK_MIN_SAMPLES
            ),
        }

    def record_promotion(
        self,
        plugin_id: str,
        segment: str,
        previous_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra promoção canary para permitir rollback futuro.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary promovido.
            previous_branch: Branch production antes da promoção.

        Returns:
            Estado registrado (persistido se DB habilitado).
        """
        cfg = self.updates.update_config(plugin_id)
        previous = previous_branch or cfg.get("production_branch", cfg["production_channel"])
        canary_plan = self.canary.build_canary_plan(plugin_id, segment)

        state = {
            "plugin_id": plugin_id,
            "segment": segment,
            "previous_branch": previous,
            "promoted_branch": canary_plan["canary_branch"],
            "production_channel": cfg["production_channel"],
            "promoted": True,
        }
        saved = self.store.save_promotion(state)
        logger.info(f"[canary-rollback] Promoção registrada {plugin_id}/{segment}")
        return saved

    def get_promotion_state(self, plugin_id: str, segment: str) -> Optional[Dict[str, Any]]:
        """
        Retorna estado de promoção ativo, se existir.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            Dict estado ou None.
        """
        state = self.store.get_active(plugin_id, segment)
        if state and not state.get("promoted", state.get("active")):
            return None
        return state

    def evaluate(self, plugin_id: str, segment: str) -> Dict[str, Any]:
        """
        Avalia se rollback é necessário por degradação de health.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            Dict decision rollback|hold|noop com health e motivo.

        Raises:
            ValueError: Segmento inválido.
        """
        health = self.health.probe_health(plugin_id, segment)
        cfg = self.rollback_config(plugin_id)
        state = self.get_promotion_state(plugin_id, segment)

        if not settings.MOBILE_EAS_UPDATE_CANARY_ENABLED:
            return self._noop(plugin_id, segment, health, "canary_disabled")

        if not cfg["auto_rollback"]:
            return self._noop(plugin_id, segment, health, "auto_rollback_disabled")

        if state is None or not state.get("promoted", state.get("active")):
            return self._noop(plugin_id, segment, health, "no_active_promotion")

        if health["samples"] < cfg["rollback_min_samples"]:
            return self._hold(plugin_id, segment, health, state, "insufficient_samples")

        if health["success_rate"] >= cfg["rollback_threshold"]:
            return self._hold(plugin_id, segment, health, state, "health_above_threshold")

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "decision": "rollback",
            "reason": "health_degraded",
            "health": health,
            "promotion_state": state,
            "rollback_plan": self.build_rollback_plan(plugin_id, segment),
        }

    def build_rollback_plan(self, plugin_id: str, segment: str) -> Dict[str, Any]:
        """
        Monta comando EAS para reverter production ao branch anterior.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.

        Returns:
            Dict com command eas channel:edit e branch anterior.

        Raises:
            ValueError: Sem promoção registrada.
        """
        state = self.get_promotion_state(plugin_id, segment)
        if not state:
            raise ValueError(f"Nenhuma promoção registrada para {plugin_id}/{segment}")

        previous_branch = state["previous_branch"]
        production_channel = state["production_channel"]
        cmd = (
            f"eas channel:edit {production_channel} --branch {previous_branch} "
            f"--non-interactive"
        )

        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "production_channel": production_channel,
            "rollback_to_branch": previous_branch,
            "from_branch": state["promoted_branch"],
            "command": cmd,
        }

    def auto_rollback(self, plugin_id: str, segment: str, force: bool = False) -> Dict[str, Any]:
        """
        Executa rollback se health degradou (ou force=true).

        Args:
            plugin_id: ID do plugin.
            segment: Segmento canary.
            force: Ignorar health e reverter imediatamente.

        Returns:
            Dict com decision e rollback_plan.

        Raises:
            ValueError: Rollback não elegível sem force.
        """
        evaluation = self.evaluate(plugin_id, segment)

        if force:
            evaluation["decision"] = "rollback"
            evaluation["reason"] = "forced"
            evaluation["rollback_plan"] = self.build_rollback_plan(plugin_id, segment)

        if evaluation["decision"] != "rollback":
            raise ValueError(f"Rollback não elegível: {evaluation.get('reason', 'hold')}")

        self.store.mark_rolled_back(plugin_id, segment)
        logger.info(f"[canary-rollback] Rollback {plugin_id}/{segment}")
        return evaluation

    @staticmethod
    def _hold(
        plugin_id: str,
        segment: str,
        health: Dict[str, Any],
        state: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """
        Resposta hold — promoção ativa, health ainda OK.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento.
            health: Probe health.
            state: Estado promoção.
            reason: Motivo do hold.

        Returns:
            Dict decision=hold.
        """
        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "decision": "hold",
            "reason": reason,
            "health": health,
            "promotion_state": state,
        }

    @staticmethod
    def _noop(
        plugin_id: str,
        segment: str,
        health: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """
        Resposta noop — rollback não aplicável.

        Args:
            plugin_id: ID do plugin.
            segment: Segmento.
            health: Probe health.
            reason: Motivo.

        Returns:
            Dict decision=noop.
        """
        return {
            "plugin_id": plugin_id,
            "segment": segment,
            "decision": "noop",
            "reason": reason,
            "health": health,
        }

    @classmethod
    def reset_state(cls, db: Optional[Session] = None) -> None:
        """
        Limpa estado in-memory e DB (testes).

        Args:
            db: Sessão SQLAlchemy opcional para limpeza persistida.

        Returns:
            None
        """
        CanaryPromotionRepository.reset_all(db)

    def list_active_promotions(self) -> List[Dict[str, Any]]:
        """
        Lista promoções canary ativas aguardando monitoramento de rollback.

        Returns:
            Lista de estados de promoção registrados.
        """
        return [
            s for s in self.store.list_active()
            if s.get("promoted", s.get("active"))
        ]

    def scan_and_rollback(self) -> Dict[str, Any]:
        """
        Varre promoções ativas e executa rollback automático quando elegível.

        Returns:
            Dict com scanned, rollbacks, holds e results por segmento.
        """
        if not settings.MOBILE_EAS_UPDATE_CANARY_ROLLBACK_WORKER_ENABLED:
            return {"enabled": False, "scanned": 0, "results": []}

        plugin_registry.load_all()
        active = self.list_active_promotions()
        results: List[Dict[str, Any]] = []
        counts = {"rollback": 0, "hold": 0, "noop": 0, "error": 0}

        for state in active:
            plugin_id = state["plugin_id"]
            segment = state["segment"]
            try:
                evaluation = self.evaluate(plugin_id, segment)
                decision = evaluation.get("decision", "noop")

                if decision == "rollback":
                    evaluation = self.auto_rollback(plugin_id, segment)
                    counts["rollback"] += 1
                elif decision == "hold":
                    counts["hold"] += 1
                else:
                    counts["noop"] += 1

                results.append(evaluation)
            except Exception as exc:
                counts["error"] += 1
                results.append(
                    {
                        "plugin_id": plugin_id,
                        "segment": segment,
                        "decision": "error",
                        "error": str(exc),
                    }
                )
                logger.warning(f"[canary-rollback-scan] Erro {plugin_id}/{segment}: {exc}")

        summary = {
            "enabled": True,
            "persist_db": settings.MOBILE_EAS_UPDATE_CANARY_PERSIST_DB,
            "scanned": len(active),
            "counts": counts,
            "results": results,
        }
        logger.info(f"[canary-rollback-scan] {summary['counts']}")
        return summary
