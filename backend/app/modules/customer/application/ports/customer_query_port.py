"""
CustomerQueryPort — leitura cross-context para booking (ADR-025 / R2-F3b).
"""
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class CustomerSnapshot:
    """
    DTO read-only de cliente para validação no create booking.

    O booking ainda usa FK ``clientes.id`` (legado). Este snapshot expõe
    ambos os IDs quando o metamodelo estiver sincronizado.

    Args:
        legacy_cliente_id: ID ``clientes`` (usado em core_bookings.customer_id).
        core_customer_id: ID ``core_customers`` se existir sync.
        company_id: Tenant.
        name: Nome exibido.
        active: Cliente ativo.
        phone: Telefone.
    """

    legacy_cliente_id: int
    company_id: int
    name: str
    active: bool
    phone: str
    core_customer_id: Optional[int] = None


class CustomerQueryPort(Protocol):
    """
    Port read-only para validar cliente no path booking core.

    ``customer_id`` nos métodos é o ID legado ``clientes.id`` (paridade FK).
    """

    def get_customer(self, customer_id: int, company_id: int) -> CustomerSnapshot:
        """
        Carrega snapshot do cliente para o tenant.

        Args:
            customer_id: ID ``clientes`` (legado / FK booking).
            company_id: Tenant.

        Returns:
            CustomerSnapshot.

        Raises:
            ValueError: Cliente inexistente ou fora do tenant.
        """
        ...
