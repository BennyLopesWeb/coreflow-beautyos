"""
EasUpdateService — OTA updates Expo (EAS Update) por plugin (CF-19).

Gera canais de update white-label alinhados aos perfis de build CF-17/18.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService

logger = get_logger("eas_update")

FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend"


class EasUpdateService:
    """
    Monta configurações EAS Update (OTA) por plugin vertical.

    Cada plugin declara ``mobile.update:`` no manifest com runtime_version
    e branches preview/production.
    """

    def __init__(self, frontend_dir: Optional[Path] = None):
        """
        Args:
            frontend_dir: Diretório raiz do frontend Expo.
        """
        self.frontend_dir = frontend_dir or FRONTEND_DIR
        self.whitelabel = EasWhitelabelService(frontend_dir=self.frontend_dir)

    def update_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve config EAS Update de um plugin.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict com channels, branches e runtime_version.
        """
        manifest = plugin_registry.get(plugin_id)
        mobile = (manifest.mobile if manifest else {}) or {}
        update = mobile.get("update", {})
        eas_cfg = self.whitelabel.mobile_eas_config(plugin_id)

        preview_channel = update.get("preview_channel", f"{plugin_id}-preview")
        production_channel = update.get("production_channel", f"{plugin_id}-production")

        return {
            "plugin_id": plugin_id,
            "eas_project_id": eas_cfg["eas_project_id"],
            "runtime_version": update.get(
                "runtime_version",
                settings.MOBILE_EAS_UPDATE_RUNTIME_VERSION,
            ),
            "preview_channel": preview_channel,
            "production_channel": production_channel,
            "preview_branch": update.get("preview_branch", preview_channel),
            "production_branch": update.get("production_branch", production_channel),
            "rollout_enabled": update.get(
                "rollout_enabled", settings.MOBILE_EAS_UPDATE_ROLLOUT_ENABLED
            ),
            "rollout_percentage": update.get(
                "rollout_percentage", settings.MOBILE_EAS_UPDATE_DEFAULT_ROLLOUT_PCT
            ),
            "rollout_stages": update.get(
                "rollout_stages", self.default_rollout_stages()
            ),
        }

    @staticmethod
    def default_rollout_stages() -> List[int]:
        """
        Retorna estágios padrão de rollout gradual (%).

        Returns:
            Lista de percentuais crescentes (ex.: [10, 25, 50, 100]).
        """
        raw = settings.MOBILE_EAS_UPDATE_ROLLOUT_STAGES
        return [int(part.strip()) for part in raw.split(",") if part.strip()]

    def build_rollout_plan(
        self,
        plugin_id: str,
        target_percentage: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Monta plano de rollout gradual OTA para um plugin.

        Args:
            plugin_id: ID do plugin vertical.
            target_percentage: Percentual alvo ou None para usar config do manifest.

        Returns:
            Dict com stages, current target e comando eas update sugerido.
        """
        cfg = self.update_config(plugin_id)
        target = target_percentage if target_percentage is not None else cfg["rollout_percentage"]
        stages = cfg["rollout_stages"]
        applicable = [stage for stage in stages if stage <= target]
        if not applicable:
            applicable = [min(stages)] if stages else [target]

        return {
            "plugin_id": plugin_id,
            "target_percentage": target,
            "stages": stages,
            "applicable_stages": applicable,
            "current_stage": applicable[-1],
            "rollout_enabled": cfg["rollout_enabled"],
            "commands": [
                self.update_command(
                    plugin_id,
                    environment="production",
                    message=f"Rollout {stage}%",
                    rollout_percentage=stage,
                )
                for stage in applicable
            ],
        }

    def build_update_profile(self, plugin_id: str, environment: str = "preview") -> Dict[str, Any]:
        """
        Monta perfil EAS Update para um plugin e ambiente.

        Args:
            plugin_id: ID do plugin vertical.
            environment: preview | production.

        Returns:
            Dict com channel, branch e runtimeVersion.
        """
        cfg = self.update_config(plugin_id)
        is_prod = environment == "production"
        channel = cfg["production_channel"] if is_prod else cfg["preview_channel"]
        branch = cfg["production_branch"] if is_prod else cfg["preview_branch"]
        rollout_pct = cfg["rollout_percentage"] if is_prod and cfg["rollout_enabled"] else 100

        profile = {
            "channel": channel,
            "branch": branch,
        }
        if is_prod and cfg["rollout_enabled"]:
            profile["rollout"] = {"percentage": rollout_pct}

        return {
            "plugin_id": plugin_id,
            "environment": environment,
            "update_key": f"{plugin_id}-{environment}",
            "channel": channel,
            "branch": branch,
            "runtime_version": cfg["runtime_version"],
            "rollout_percentage": rollout_pct,
            "profile": profile,
        }

    def list_update_profiles(self) -> List[Dict[str, Any]]:
        """
        Lista perfis EAS Update de todos os plugins (preview + production).

        Returns:
            Lista de perfis update por plugin.
        """
        profiles: List[Dict[str, Any]] = []
        for manifest in plugin_registry.list_all():
            profiles.append(self.build_update_profile(manifest.plugin_id, "preview"))
            profiles.append(self.build_update_profile(manifest.plugin_id, "production"))
        return profiles

    def update_command(
        self,
        plugin_id: str,
        environment: str = "preview",
        message: str = "OTA update",
        rollout_percentage: Optional[int] = None,
    ) -> str:
        """
        Gera comando CLI ``eas update`` para um plugin.

        Args:
            plugin_id: ID do plugin.
            environment: preview | production.
            message: Mensagem do update.
            rollout_percentage: Percentual gradual (production only).

        Returns:
            Comando eas update pronto para execução.
        """
        profile = self.build_update_profile(plugin_id, environment)
        cmd = (
            f"eas update --branch {profile['branch']} --channel {profile['channel']} "
            f"--message \"{message}\" --non-interactive"
        )
        pct = rollout_percentage
        if pct is None and environment == "production":
            pct = profile.get("rollout_percentage")
        if pct is not None and environment == "production" and pct < 100:
            cmd += f" --rollout-percentage {pct}"
        return cmd

    def generate_update_file(self) -> Dict[str, Any]:
        """
        Gera ``frontend/eas.update.json`` com canais OTA por plugin.

        Returns:
            Documento JSON gravado no disco.
        """
        plugins: Dict[str, Any] = {}
        updates: Dict[str, Any] = {}

        for manifest in plugin_registry.list_all():
            pid = manifest.plugin_id
            plugins[pid] = self.update_config(pid)
            for env in ("preview", "production"):
                built = self.build_update_profile(pid, env)
                updates[built["update_key"]] = built["profile"]

        document = {
            "version": settings.APP_VERSION,
            "update_enabled": settings.MOBILE_EAS_UPDATE_ENABLED,
            "rollout_default_stages": self.default_rollout_stages(),
            "plugins": plugins,
            "update": updates,
            "usage": "./scripts/eas-update.sh beauty preview \"Fix push\"",
            "rollout_usage": "./scripts/eas-update-rollout.sh sports production 50",
        }

        target = self.frontend_dir / "eas.update.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2), encoding="utf-8")
        logger.info(f"[eas-update] eas.update.json gerado → {target}")
        return document
