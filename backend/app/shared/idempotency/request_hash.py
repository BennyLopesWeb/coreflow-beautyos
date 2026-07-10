"""
Hash estável de corpo de request para idempotência.
"""
import hashlib
import json
from typing import Any, Dict


def compute_request_hash(body: Dict[str, Any]) -> str:
    """
    Calcula SHA-256 de representação JSON canônica do body.

    Args:
        body: Dict serializável (campos do DTO de create booking).

    Returns:
        Hex digest de 64 caracteres.
    """
    normalized = json.dumps(body, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
