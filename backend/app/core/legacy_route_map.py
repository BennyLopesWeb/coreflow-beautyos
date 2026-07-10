"""
LegacyRouteMap — mapa Legado / BeautyOS → CoreFlow v1 (R1-F1).

Usado por enforcement, telemetria e documentação API.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.core.core_enforcement import LEGACY_WRITE_ROUTES, LegacyWriteRoute


@dataclass(frozen=True)
class RouteMapping:
    """
    Mapeamento entre rota legada/beauty e sucessor CoreFlow v1.

    Attributes:
        layer: legacy | beautyos | core | identity.
        method: Método HTTP ou ``*`` para qualquer.
        legacy_path: Path legado ou beauty.
        core_path: Path CoreFlow v1 sucessor.
        domain: Domínio metamodelo (booking, payment, …).
        notes: Observações de paridade.
    """

    layer: str
    method: str
    legacy_path: str
    core_path: str
    domain: str
    notes: str = ""


def _from_enforcement(rule: LegacyWriteRoute, layer: str, domain: str) -> RouteMapping:
    """
    Converte regra de enforcement em RouteMapping.

    Args:
        rule: LegacyWriteRoute existente.
        layer: Camada API.
        domain: Domínio metamodelo.

    Returns:
        RouteMapping correspondente.
    """
    return RouteMapping(
        layer=layer,
        method=rule.method,
        legacy_path=rule.prefix,
        core_path=rule.successor,
        domain=domain,
        notes="write enforcement",
    )


# Escritas com enforcement (fonte: core_enforcement.py)
_WRITE_MAPPINGS: Tuple[RouteMapping, ...] = (
    _from_enforcement(LegacyWriteRoute("POST", "/agenda/agendamentos", "/v1/bookings"), "legacy", "booking"),
    _from_enforcement(LegacyWriteRoute("POST", "/agendamentos", "/v1/bookings"), "legacy", "booking"),
    _from_enforcement(LegacyWriteRoute("PUT", "/agendamentos", "/v1/bookings"), "legacy", "booking"),
    _from_enforcement(LegacyWriteRoute("DELETE", "/agendamentos", "/v1/bookings"), "legacy", "booking"),
    _from_enforcement(LegacyWriteRoute("POST", "/reservations", "/v1/bookings"), "beautyos", "booking"),
    _from_enforcement(LegacyWriteRoute("PUT", "/reservations", "/v1/bookings"), "beautyos", "booking"),
    _from_enforcement(LegacyWriteRoute("POST", "/payments/deposit", "/v1/payments"), "beautyos", "payment"),
    _from_enforcement(LegacyWriteRoute("POST", "/payments/final", "/v1/payments"), "beautyos", "payment"),
    _from_enforcement(LegacyWriteRoute("POST", "/fila", "/v1/waitlist"), "legacy", "waitlist"),
    _from_enforcement(LegacyWriteRoute("POST", "/pagamentos/sinal", "/v1/payments"), "legacy", "payment"),
    _from_enforcement(LegacyWriteRoute("POST", "/financeiro/saida", "/v1/invoices"), "legacy", "invoice"),
)

# Leituras principais (documentação — sem enforcement write)
_READ_MAPPINGS: Tuple[RouteMapping, ...] = (
    RouteMapping("legacy", "GET", "/agenda/agendamentos", "/v1/bookings", "booking", "list"),
    RouteMapping("legacy", "GET", "/agendamentos", "/v1/bookings", "booking", "list"),
    RouteMapping("legacy", "GET", "/trancas", "/v1/catalogs", "catalog", "list"),
    RouteMapping("legacy", "GET", "/clientes", "/v1/customers", "customer", "list"),
    RouteMapping("legacy", "GET", "/fila", "/v1/waitlist", "waitlist", "list"),
    RouteMapping("legacy", "GET", "/financeiro", "/v1/invoices", "invoice", "list"),
    RouteMapping("beautyos", "GET", "/reservations", "/v1/bookings", "booking", "list"),
    RouteMapping("beautyos", "GET", "/payments", "/v1/payments", "payment", "list"),
    RouteMapping("beautyos", "GET", "/queue", "/v1/waitlist", "waitlist", "operational_queue"),
    RouteMapping("core", "GET", "/v1/scheduling/availability", "/v1/scheduling/availability", "scheduling", "native"),
    RouteMapping("identity", "POST", "/auth/login", "/auth/login", "identity", "native"),
    RouteMapping("identity", "GET", "/companies", "/companies", "company", "native"),
)


def all_route_mappings() -> List[RouteMapping]:
    """
    Lista completa de mapeamentos legado → core.

    Returns:
        Lista ordenada por layer e legacy_path.
    """
    combined = list(_WRITE_MAPPINGS) + list(_READ_MAPPINGS)
    return sorted(combined, key=lambda m: (m.layer, m.legacy_path, m.method))


def route_mapping_document() -> dict:
    """
    Documento JSON do mapa para API e export.

    Returns:
        Dict version, mappings, write_count, read_count.
    """
    mappings = all_route_mappings()
    return {
        "version": "1.0",
        "description": "Legado / BeautyOS → CoreFlow v1",
        "write_mappings": len(_WRITE_MAPPINGS),
        "read_mappings": len(_READ_MAPPINGS),
        "mappings": [
            {
                "layer": m.layer,
                "method": m.method,
                "legacy_path": m.legacy_path,
                "core_path": m.core_path,
                "domain": m.domain,
                "notes": m.notes,
            }
            for m in mappings
        ],
    }


def classify_api_layer(path: str) -> str:
    """
    Classifica path HTTP em camada API para telemetria.

    Args:
        path: Path da requisição (sem query).

    Returns:
        legacy | beautyos | core | identity | platform | other
    """
    if path.startswith("/v1/platform"):
        return "platform"
    if path.startswith("/v1/"):
        return "core"
    if path.startswith("/auth") or path.startswith("/companies"):
        return "identity"
    beautyos_prefixes = ("/reservations", "/payments", "/queue")
    if any(path == p or path.startswith(f"{p}/") for p in beautyos_prefixes):
        return "beautyos"
    legacy_prefixes = (
        "/agenda",
        "/agendamentos",
        "/trancas",
        "/clientes",
        "/fila",
        "/financeiro",
        "/pagamentos",
        "/admin",
        "/notifications",
        "/webhook",
    )
    if any(path == p or path.startswith(f"{p}/") for p in legacy_prefixes):
        return "legacy"
    return "other"


def find_core_successor(method: str, path: str) -> Optional[str]:
    """
    Encontra path core sucessor para rota legada/beauty.

    Args:
        method: Método HTTP.
        path: Path da requisição.

    Returns:
        core_path ou None.
    """
    method = method.upper()
    for mapping in _WRITE_MAPPINGS:
        if mapping.method != method:
            continue
        if path == mapping.legacy_path or path.startswith(f"{mapping.legacy_path}/"):
            return mapping.core_path
    for mapping in _READ_MAPPINGS:
        if mapping.method not in ("*", method):
            continue
        if path == mapping.legacy_path or path.startswith(f"{mapping.legacy_path}/"):
            return mapping.core_path
    return None
