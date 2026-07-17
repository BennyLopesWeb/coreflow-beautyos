"""
Value objects do Resource Engine (R2-F3 / ADR-007).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceTypeId:
    """
    Identificador de tipo de resource declarado no plugin.

    Attributes:
        value: ID canônico (ex.: chair, court, room).
    """

    value: str

    def __post_init__(self) -> None:
        """
        Normaliza e valida type id.

        Raises:
            ValueError: Se vazio.
        """
        normalized = (self.value or "").strip().lower()
        if not normalized:
            raise ValueError("resource_type inválido")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Capacity:
    """
    Capacidade simultânea de um resource (>= 1).

    Attributes:
        value: Número de vagas paralelas.
    """

    value: int

    def __post_init__(self) -> None:
        """
        Valida capacity mínima.

        Raises:
            InvalidResourceCapacityError: Se value < 1.
        """
        from app.modules.resource.domain.exceptions import InvalidResourceCapacityError

        if self.value < 1:
            raise InvalidResourceCapacityError("capacity must be >= 1")
