"""
ClockPort — abstração de relógio para policy e testes (R2-F2b / Q7).
"""
from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """
    Fornece instante corrente em UTC para ports de policy.

    Evita acoplamento a ``datetime.now()`` no domínio e adapters testáveis.
    """

    def now_utc(self) -> datetime:
        """
        Retorna datetime timezone-aware em UTC.

        Returns:
            Instante atual em UTC.
        """
        ...
