"""
Utilitário para colunas Enum persistirem o `.value` (string) no SQLite.
"""
import enum
from typing import Type, TypeVar
from sqlalchemy import Enum as SQLEnum

E = TypeVar("E", bound=enum.Enum)


def enum_values(enum_cls: Type[E]) -> SQLEnum:
    """
    Cria coluna Enum que grava e lê os valores string do enum Python.

    Args:
        enum_cls: Classe enum (str, enum.Enum).

    Returns:
        Tipo SQLAlchemy Enum configurado para values.
    """
    return SQLEnum(enum_cls, values_callable=lambda members: [m.value for m in members])
