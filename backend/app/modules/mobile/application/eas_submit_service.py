"""
EasSubmitService — submit automatizado App Store / Play Store por plugin (CF-18).
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.plugin.registry import plugin_registry
from app.modules.mobile.application.eas_whitelabel_service import EasWhitelabelService

logger = get_logger("eas_submit")

FRONTEND_DIR = Path(__file__).resolve().parents[5] / "frontend"


class EasSubmitService:
    """
    Gera perfis EAS Submit white-label por plugin vertical.

    Cada plugin pode declarar ``mobile.submit:`` no manifest com ascAppId,
    appleId, track Play Store e caminho da service account.
    """

    def __init__(self, frontend_dir: Optional[Path] = None):
        """
        Args:
            frontend_dir: Diretório raiz do frontend Expo.
        """
        self.frontend_dir = frontend_dir or FRONTEND_DIR
        self.whitelabel = EasWhitelabelService(frontend_dir=self.frontend_dir)

    def submit_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Resolve config de submit para um plugin.

        Args:
            plugin_id: beauty, sports, clinic.

        Returns:
            Dict com ios/android submit settings e profile_key.
        """
        manifest = plugin_registry.get(plugin_id)
        mobile = (manifest.mobile if manifest else {}) or {}
        submit = mobile.get("submit", {})
        eas_cfg = self.whitelabel.mobile_eas_config(plugin_id)

        ios_submit = submit.get("ios", {})
        android_submit = submit.get("android", {})

        return {
            "plugin_id": plugin_id,
            "profile_key": f"{plugin_id}-production",
            "app_name": eas_cfg["app_name"],
            "ios_bundle_id": eas_cfg["ios_bundle_id"],
            "android_package": eas_cfg["android_package"],
            "ios": {
                "appleId": ios_submit.get("apple_id", settings.MOBILE_EAS_SUBMIT_APPLE_ID),
                "ascAppId": ios_submit.get("asc_app_id", settings.MOBILE_EAS_SUBMIT_ASC_APP_ID),
                "appleTeamId": ios_submit.get(
                    "apple_team_id", settings.MOBILE_EAS_SUBMIT_APPLE_TEAM_ID
                ),
            },
            "android": {
                "serviceAccountKeyPath": android_submit.get(
                    "service_account_key",
                    settings.MOBILE_EAS_SUBMIT_ANDROID_KEY_PATH,
                ),
                "track": android_submit.get("track", settings.MOBILE_EAS_SUBMIT_ANDROID_TRACK),
            },
        }

    def build_submit_profile(self, plugin_id: str) -> Dict[str, Any]:
        """
        Monta fragmento eas.json ``submit.{plugin_id}-production``.

        Args:
            plugin_id: ID do plugin vertical.

        Returns:
            Dict no formato EAS submit profile.
        """
        cfg = self.submit_config(plugin_id)
        return {
            "plugin_id": plugin_id,
            "submit_key": f"{plugin_id}-production",
            "profile": {
                "extends": "production",
                "ios": cfg["ios"],
                "android": cfg["android"],
            },
        }

    def list_submit_profiles(self) -> List[Dict[str, Any]]:
        """
        Lista perfis submit de todos os plugins.

        Returns:
            Lista de configs submit por plugin.
        """
        return [self.build_submit_profile(p.plugin_id) for p in plugin_registry.list_all()]

    def submit_command(self, plugin_id: str, platform: str = "all") -> str:
        """
        Gera comando CLI ``eas submit`` para um plugin.

        Args:
            plugin_id: ID do plugin.
            platform: ios | android | all.

        Returns:
            String do comando eas submit pronto para execução.
        """
        submit_key = f"{plugin_id}-production"
        return (
            f"eas submit --profile {submit_key} --platform {platform} "
            f"--non-interactive --latest"
        )

    def generate_submit_file(self) -> Dict[str, Any]:
        """
        Gera ``frontend/eas.submit.json`` com perfis submit por plugin.

        Returns:
            Documento JSON gravado no disco.
        """
        submit_profiles: Dict[str, Any] = {}
        plugins: Dict[str, Any] = {}

        for manifest in plugin_registry.list_all():
            pid = manifest.plugin_id
            built = self.build_submit_profile(pid)
            submit_profiles[built["submit_key"]] = built["profile"]
            plugins[pid] = self.submit_config(pid)

        document = {
            "version": settings.APP_VERSION,
            "submit_enabled": settings.MOBILE_EAS_SUBMIT_ENABLED,
            "plugins": plugins,
            "submit": submit_profiles,
            "usage": "./scripts/eas-submit.sh beauty ios",
        }

        target = self.frontend_dir / "eas.submit.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2), encoding="utf-8")
        logger.info(f"[eas-submit] eas.submit.json gerado → {target}")
        return document
