"""
Value objects e enums do aggregate Booking (ADR-009 / ADR-026).
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class BookingLifecycleStatus(str, Enum):
    """
    Estado de ciclo de vida canônico do Core (R2-F1: create → pending).

    Mapeia para ``ReservationStatus`` legado na camada de infraestrutura.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SyncStatus(str, Enum):
    """
    Estado de sincronização core ↔ legado (ADR-024).

    Attributes:
        SYNCED: Projeção legado consistente.
        PENDING: Aguardando projeção.
        DRIFT: Divergência detectada (reconciliation F5).
    """

    SYNCED = "synced"
    PENDING = "pending"
    DRIFT = "drift"


@dataclass(frozen=True)
class TimeSlot:
    """
    Intervalo de tempo de uma reserva.

    Args:
        starts_at: Início do slot (timezone-aware quando possível).
        ends_at: Fim do slot.
    """

    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        """
        Valida INV-B2: starts_at < ends_at.

        Raises:
            ValueError: Se intervalo inválido.
        """
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at must be before ends_at")


@dataclass(frozen=True)
class MoneySnapshot:
    """
    Snapshot monetário imutável no momento da criação.

    Args:
        price_total: Valor total.
        deposit_pct: Percentual de sinal (0.30 = 30%).
        deposit_amount: Valor do sinal.
        remaining_amount: Valor restante.
    """

    price_total: Decimal
    deposit_pct: Decimal
    deposit_amount: Decimal
    remaining_amount: Decimal


@dataclass(frozen=True)
class LegacyReference:
    """
    Referência à projeção legado (ADR-024).

    Args:
        legacy_agendamento_id: ID ``agendamentos.id`` quando projetado.
        sync_status: Estado de sync com legado.
    """

    legacy_agendamento_id: int | None = None
    sync_status: SyncStatus = SyncStatus.PENDING
