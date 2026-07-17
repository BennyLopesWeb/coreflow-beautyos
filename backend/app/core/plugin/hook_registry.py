"""
Typed Hook Registry — Plugin Engine (ADR-011 / R2-F4).

Resolve handlers apenas sob ``app.plugins.*`` (sem eval livre).
Dispatch gated por ``plugin.engine.enabled``.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.core.feature_flags import feature_flags
from app.core.logging_config import get_logger
from app.core.plugin.hooks import HOOK_NAMES
from app.core.plugin.manifest import PluginManifest

logger = get_logger("hook_registry")

_ALLOWED_PREFIX = "app.plugins."


@dataclass(frozen=True)
class HandlerRef:
    """
    Referência tipada a um handler de plugin.

    Args:
        plugin_id: Plugin que registrou o handler.
        hook_name: Nome do hook (ADR-011).
        handler: Callable ``(payload) -> Any``.
        async_mode: Se True, execução preferencialmente assíncrona (F4: sync + log).
        handler_path: Path declarado no manifest (auditoria).
    """

    plugin_id: str
    hook_name: str
    handler: Callable[[Any], Any]
    async_mode: bool = False
    handler_path: str = ""


class HookRegistry:
    """
    Registry ``hook_name → list[HandlerRef]``.

    Carrega handlers a partir dos manifests; ``dispatch`` é no-op quando
    ``plugin.engine.enabled`` está OFF.

    Attributes:
        _handlers: Mapa hook → refs.
    """

    def __init__(self):
        self._handlers: Dict[str, List[HandlerRef]] = {}

    def clear(self) -> None:
        """
        Remove todos os handlers registrados.

        Returns:
            None
        """
        self._handlers.clear()

    def register_from_manifest(self, manifest: PluginManifest) -> int:
        """
        Registra handlers tipados a partir do manifest do plugin.

        Args:
            manifest: Manifest com ``hooks`` (str ou {handler, async}).

        Returns:
            Quantidade de handlers registrados com sucesso.
        """
        count = 0
        for hook_name, binding in (manifest.hooks or {}).items():
            if hook_name not in HOOK_NAMES:
                logger.warning(
                    f"[HookRegistry] hook desconhecido ignorado: "
                    f"{manifest.plugin_id}/{hook_name}"
                )
                continue
            handler_path, async_mode = manifest.resolve_hook_binding(hook_name)
            if not handler_path:
                continue
            try:
                handler = self._resolve_callable(handler_path)
            except Exception as exc:
                logger.error(
                    f"[HookRegistry] falha ao resolver {handler_path}: {exc}"
                )
                continue
            ref = HandlerRef(
                plugin_id=manifest.plugin_id,
                hook_name=hook_name,
                handler=handler,
                async_mode=async_mode,
                handler_path=handler_path,
            )
            self._handlers.setdefault(hook_name, []).append(ref)
            count += 1
            logger.info(
                f"[HookRegistry] registered {manifest.plugin_id}:{hook_name} → {handler_path}"
            )
        return count

    def install_from_registry(self, manifests: List[PluginManifest]) -> int:
        """
        Limpa e reinstala handlers de uma lista de manifests.

        Args:
            manifests: Manifests carregados pelo PluginRegistry.

        Returns:
            Total de handlers instalados.
        """
        self.clear()
        total = 0
        for manifest in manifests:
            total += self.register_from_manifest(manifest)
        return total

    def list_handlers(self, hook_name: Optional[str] = None) -> List[HandlerRef]:
        """
        Lista handlers registrados.

        Args:
            hook_name: Filtra por hook; None = todos.

        Returns:
            Lista de HandlerRef.
        """
        if hook_name:
            return list(self._handlers.get(hook_name, []))
        refs: List[HandlerRef] = []
        for items in self._handlers.values():
            refs.extend(items)
        return refs

    def dispatch(self, hook_name: str, payload: Any) -> int:
        """
        Invoca handlers do hook com payload tipado.

        Core TX já deve estar commitada. Exceções do handler são logadas
        e não propagam (isolamento F4 — DLQ deferido).

        Args:
            hook_name: Nome ADR-011.
            payload: DTO tipado correspondente.

        Returns:
            Quantidade de handlers invocados com sucesso (0 se flag OFF).
        """
        if not feature_flags.is_enabled("plugin.engine.enabled"):
            return 0
        if hook_name not in HOOK_NAMES:
            logger.warning(f"[HookRegistry] dispatch hook inválido: {hook_name}")
            return 0

        refs = self._handlers.get(hook_name, [])
        ok = 0
        for ref in refs:
            try:
                ref.handler(payload)
                ok += 1
            except Exception as exc:
                logger.error(
                    f"[HookRegistry] handler failed "
                    f"{ref.plugin_id}:{hook_name} ({ref.handler_path}): {exc}",
                    exc_info=True,
                )
        return ok

    def _resolve_callable(self, handler_path: str) -> Callable[[Any], Any]:
        """
        Resolve ``app.plugins.*.module`` ou ``app.plugins.*.module.attr``.

        Args:
            handler_path: Path absoluto Python sob ``app.plugins.``.

        Returns:
            Callable do handler.

        Raises:
            ValueError: Prefixo não permitido.
            ImportError / AttributeError: Resolução falhou.
        """
        if not handler_path.startswith(_ALLOWED_PREFIX):
            raise ValueError(
                f"Handler fora de {_ALLOWED_PREFIX}: {handler_path}"
            )
        try:
            module = importlib.import_module(handler_path)
            handler = getattr(module, "handle", None)
            if callable(handler):
                return handler
        except ModuleNotFoundError:
            pass

        module_path, _, attr = handler_path.rpartition(".")
        if not module_path or not attr:
            raise ImportError(f"Handler path inválido: {handler_path}")
        module = importlib.import_module(module_path)
        handler = getattr(module, attr)
        if not callable(handler):
            raise AttributeError(f"{handler_path} não é callable")
        return handler


hook_registry = HookRegistry()
