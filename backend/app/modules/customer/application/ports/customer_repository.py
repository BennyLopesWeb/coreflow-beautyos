"""
CustomerRepository port (ADR-030 / R2-F3b).
"""
from typing import List, Optional, Protocol

from app.modules.customer.models import CoreCustomer


class CustomerRepository(Protocol):
    """
    Port de persistência/leitura de ``core_customers``.

    Implementação: ``SqlAlchemyCustomerRepository``.
    Hexagonal lite — ORM metamodelo, sem aggregate.

    Methods:
        get_by_id: Customer core por id + tenant.
        get_by_legacy_id: Resolve via ``legacy_cliente_id``.
        find_by_phone: Busca por telefone no tenant.
        list_by_company: Lista do tenant.
        save: Persiste (upsert).
    """

    def get_by_id(self, customer_id: int, company_id: int) -> Optional[CoreCustomer]:
        """
        Carrega core_customer por id e tenant.

        Args:
            customer_id: ID ``core_customers``.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        ...

    def get_by_legacy_id(
        self, legacy_cliente_id: int, company_id: int
    ) -> Optional[CoreCustomer]:
        """
        Resolve core_customer a partir de ``clientes.id``.

        Args:
            legacy_cliente_id: ID legado.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        ...

    def find_by_phone(self, phone: str, company_id: int) -> Optional[CoreCustomer]:
        """
        Busca por telefone no tenant.

        Args:
            phone: Telefone.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        ...

    def list_by_company(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCustomer]:
        """
        Lista customers do tenant.

        Args:
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista de CoreCustomer.
        """
        ...

    def save(self, customer: CoreCustomer) -> CoreCustomer:
        """
        Persiste customer.

        Args:
            customer: Entidade ORM.

        Returns:
            CoreCustomer com id.
        """
        ...
