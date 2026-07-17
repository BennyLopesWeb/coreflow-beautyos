"""
Serviço read-only de Customer — facade sobre CustomerRepository (R2-F3b).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.customer.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)
from app.modules.customer.models import CoreCustomer


class CustomerService:
    """
    Consultas de leitura para ``core_customers``.

    Delega ao ``CustomerRepository`` (ADR-030). Mantém API pública estável
    para routers existentes.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db
        self._repo = SqlAlchemyCustomerRepository(db)

    def list_customers(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCustomer]:
        """
        Lista clientes do tenant.

        Args:
            company_id: ID da empresa.
            active_only: Filtra apenas ativos.

        Returns:
            Lista de CoreCustomer.
        """
        return self._repo.list_by_company(company_id, active_only=active_only)

    def get_customer(self, customer_id: int, company_id: int) -> CoreCustomer:
        """
        Obtém customer por ID com escopo de tenant.

        Args:
            customer_id: ID core_customers.
            company_id: ID da empresa.

        Returns:
            CoreCustomer.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = self._repo.get_by_id(customer_id, company_id)
        if not row:
            raise NotFoundError("Customer", str(customer_id))
        return row

    def find_by_phone(self, phone: str, company_id: int) -> Optional[CoreCustomer]:
        """
        Busca customer por telefone no tenant.

        Args:
            phone: Telefone.
            company_id: ID da empresa.

        Returns:
            CoreCustomer ou None.
        """
        return self._repo.find_by_phone(phone, company_id)
