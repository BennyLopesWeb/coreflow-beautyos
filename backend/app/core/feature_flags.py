"""
FeatureFlagService — flags de migração CoreFlow (R1-F1 / RFC-002).

Protege rollout incremental de booking core, AI core, workflow e plugin engine.
"""
from typing import Any, Dict

from app.core.config import settings


class FeatureFlagService:
    """
    Resolve feature flags de plataforma a partir de settings.

    Flags seguem convenção ``FEATURE_<NAME>_ENABLED`` mapeadas para
    chaves públicas ``domain.component.enabled``.
    """

    _FLAG_MAP: Dict[str, str] = {
        "booking.core.enabled": "FEATURE_BOOKING_CORE_ENABLED",
        "ai.core.enabled": "FEATURE_AI_CORE_ENABLED",
        "workflow.enabled": "FEATURE_WORKFLOW_ENABLED",
        "plugin.engine.enabled": "FEATURE_PLUGIN_ENGINE_ENABLED",
        "legacy.telemetry.enabled": "FEATURE_LEGACY_TELEMETRY_ENABLED",
    }

    def is_enabled(self, flag_key: str) -> bool:
        """
        Verifica se uma feature flag está habilitada.

        Args:
            flag_key: Chave pública (ex.: ``booking.core.enabled``).

        Returns:
            True se habilitada; False se desconhecida ou desligada.

        Raises:
            KeyError: Se flag_key não está registrada no mapa.
        """
        setting_name = self._FLAG_MAP.get(flag_key)
        if setting_name is None:
            raise KeyError(f"Feature flag desconhecida: {flag_key}")
        return bool(getattr(settings, setting_name))

    def all_flags(self) -> Dict[str, Any]:
        """
        Retorna snapshot de todas as flags registradas.

        Returns:
            Dict flag_key → {enabled, setting_name}.
        """
        result: Dict[str, Any] = {}
        for flag_key, setting_name in self._FLAG_MAP.items():
            result[flag_key] = {
                "enabled": bool(getattr(settings, setting_name)),
                "setting": setting_name,
            }
        return result


feature_flags = FeatureFlagService()
