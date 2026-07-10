"""
Consultas read-only de Customer genérico CoreFlow.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.customer.domain.models import CoreCustomer


class CustomerQueryService:
    """
    Serviço de leitura para core_customers.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

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
        query = self.db.query(CoreCustomer).filter(
            CoreCustomer.company_id == company_id,
            CoreCustomer.deleted_at.is_(None),
        )
        if active_only:
            query = query.filter(CoreCustomer.active.is_(True))
        return query.order_by(CoreCustomer.name).all()

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
        row = (
            self.db.query(CoreCustomer)
            .filter(
                CoreCustomer.id == customer_id,
                CoreCustomer.company_id == company_id,
                CoreCustomer.deleted_at.is_(None),
            )
            .first()
        )
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
        return (
            self.db.query(CoreCustomer)
            .filter(
                CoreCustomer.phone == phone,
                CoreCustomer.company_id == company_id,
                CoreCustomer.deleted_at.is_(None),
            )
            .first()
        )
