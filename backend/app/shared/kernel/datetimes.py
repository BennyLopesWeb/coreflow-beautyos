"""
Utilitários de datetime para o shared kernel.

Padroniza comparação e persistência com valores naive em UTC, compatíveis
com SQLite/SQLAlchemy e serviços legados que usam ``datetime.now()`` naive.
"""
from __future__ import annotations

from datetime import datetime, timezone


def as_naive_utc(value: datetime) -> datetime:
    """
    Converte um datetime para naive em UTC.

    Args:
        value: Datetime de entrada (naive ou timezone-aware).

    Returns:
        Datetime sem ``tzinfo``, equivalente ao instante em UTC. Se ``value``
        já for naive, retorna cópia sem alteração de relógio (tratado como
        horário local/UTC já alinhado ao restante do sistema legado).
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=None)
    return value.astimezone(timezone.utc).replace(tzinfo=None)
