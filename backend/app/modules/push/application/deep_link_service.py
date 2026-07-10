"""
DeepLinkService — constrói URLs custom scheme e universal links (CF-12/13).
"""
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.plugin.registry import plugin_registry


class DeepLinkService:
    """
    Resolve deep links declarados em ``manifest.yaml`` → ``sdk.deep_links``.

    Formatos:
    - Custom scheme: ``trancapro://{tenant}{path}``
    - Universal link: ``https://{host}/{tenant}{path}``
    """

    DEFAULT_ROUTES: Dict[str, str] = {
        "booking_detail": "/bookings/{booking_id}",
        "booking_admin": "/admin/reservas/{booking_id}",
        "catalog_detail": "/agendar/{catalog_id}",
        "bookings_list": "/agendamentos",
        "waitlist": "/fila",
    }

    def _resolve_routes(self, plugin_id: str) -> Dict[str, str]:
        """
        Mescla rotas default com rotas do manifest do plugin.

        Args:
            plugin_id: ID do plugin.

        Returns:
            Mapa route_key → path template.
        """
        manifest = plugin_registry.get(plugin_id) or plugin_registry.require("beauty")
        deep_links = manifest.sdk.get("deep_links", {})
        return {**self.DEFAULT_ROUTES, **deep_links.get("routes", {})}

    def _format_path(self, plugin_id: str, route_key: str, **params: Any) -> str:
        """
        Formata path de rota com placeholders.

        Args:
            plugin_id: ID do plugin.
            route_key: Chave da rota.
            **params: Placeholders (booking_id, etc.).

        Returns:
            Path relativo (ex.: /bookings/42).
        """
        routes = self._resolve_routes(plugin_id)
        template = routes.get(route_key, f"/{route_key}")
        return template.format(**params)

    def build(
        self,
        company_slug: str,
        plugin_id: str,
        route_key: str,
        **params: Any,
    ) -> str:
        """
        Monta URL custom scheme para um tenant e rota do manifest.

        Args:
            company_slug: Slug público da empresa (ex.: salao-demo).
            plugin_id: Plugin ativo (beauty, sports, clinic).
            route_key: Chave em sdk.deep_links.routes (ex.: booking_detail).
            **params: Placeholders da rota (booking_id, catalog_id, etc.).

        Returns:
            URL completa no formato scheme://slug/path.
        """
        manifest = plugin_registry.get(plugin_id) or plugin_registry.require("beauty")
        deep_links = manifest.sdk.get("deep_links", {})
        scheme = deep_links.get("scheme") or settings.MOBILE_DEEP_LINK_SCHEME
        path = self._format_path(plugin_id, route_key, **params)
        prefix = deep_links.get("prefix", "")
        if prefix and not prefix.startswith("/"):
            prefix = f"/{prefix}"
        return f"{scheme}://{company_slug}{prefix}{path}"

    def build_universal(
        self,
        company_slug: str,
        plugin_id: str,
        route_key: str,
        **params: Any,
    ) -> str:
        """
        Monta universal link HTTPS para iOS/Android App Links.

        Args:
            company_slug: Slug público da empresa.
            plugin_id: Plugin ativo.
            route_key: Chave da rota no manifest.
            **params: Placeholders da rota.

        Returns:
            URL https://host/tenant/path.
        """
        manifest = plugin_registry.get(plugin_id) or plugin_registry.require("beauty")
        deep_links = manifest.sdk.get("deep_links", {})
        host = (
            deep_links.get("universal_host")
            or settings.MOBILE_UNIVERSAL_LINK_HOST
        )
        path = self._format_path(plugin_id, route_key, **params)
        prefix = deep_links.get("prefix", "")
        if prefix and not prefix.startswith("/"):
            prefix = f"/{prefix}"
        tenant_path = f"/{company_slug}{prefix}{path}"
        return f"https://{host}{tenant_path}"

    def build_pair(
        self,
        company_slug: str,
        plugin_id: str,
        route_key: str,
        **params: Any,
    ) -> Dict[str, str]:
        """
        Retorna par scheme + universal link para push mobile.

        Args:
            company_slug: Slug do tenant.
            plugin_id: Plugin ativo.
            route_key: Chave da rota.
            **params: Placeholders.

        Returns:
            Dict com deep_link e universal_link.
        """
        return {
            "deep_link": self.build(company_slug, plugin_id, route_key, **params),
            "universal_link": self.build_universal(
                company_slug, plugin_id, route_key, **params
            ),
        }

    def resolve_config(self, plugin_id: str) -> Dict[str, Any]:
        """
        Retorna configuração de deep links de um plugin para o frontend.

        Args:
            plugin_id: Identificador do plugin.

        Returns:
            Dict com scheme, universal_host, prefix e mapa de rotas.
        """
        manifest = plugin_registry.get(plugin_id) or plugin_registry.require("beauty")
        deep_links = manifest.sdk.get("deep_links", {})
        return {
            "scheme": deep_links.get("scheme") or settings.MOBILE_DEEP_LINK_SCHEME,
            "universal_host": (
                deep_links.get("universal_host")
                or settings.MOBILE_UNIVERSAL_LINK_HOST
            ),
            "prefix": deep_links.get("prefix", ""),
            "routes": self._resolve_routes(plugin_id),
        }

    def route_for_event(self, event_type: str) -> Optional[str]:
        """
        Mapeia tipo de evento outbox para chave de rota deep link.

        Args:
            event_type: Nome do evento (ex.: booking.approved).

        Returns:
            Chave de rota ou None se evento não gera push com link.
        """
        mapping = {
            "booking.created": "booking_admin",
            "booking.approved": "booking_detail",
            "booking.rejected": "booking_detail",
            "payment.deposit.confirmed": "booking_detail",
            "reservation.created": "booking_admin",
        }
        return mapping.get(event_type)
