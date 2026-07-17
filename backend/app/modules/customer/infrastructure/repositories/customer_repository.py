"""
SQLAlchemy adapter para CustomerRepository (ADR-030 / R2-F3b).
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.customer.models import CoreCustomer


class SqlAlchemyCustomerRepository:
    """
    Persistência/leitura de ``core_customers``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, customer_id: int, company_id: int) -> Optional[CoreCustomer]:
        """
        Carrega por id core + tenant.

        Args:
            customer_id: ID ``core_customers``.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        return (
            self._db.query(CoreCustomer)
            .filter(
                CoreCustomer.id == customer_id,
                CoreCustomer.company_id == company_id,
                CoreCustomer.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_legacy_id(
        self, legacy_cliente_id: int, company_id: int
    ) -> Optional[CoreCustomer]:
        """
        Resolve via ``legacy_cliente_id``.

        Args:
            legacy_cliente_id: ID ``clientes``.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        return (
            self._db.query(CoreCustomer)
            .filter(
                CoreCustomer.legacy_cliente_id == legacy_cliente_id,
                CoreCustomer.company_id == company_id,
                CoreCustomer.deleted_at.is_(None),
            )
            .first()
        )

    def find_by_phone(self, phone: str, company_id: int) -> Optional[CoreCustomer]:
        """
        Busca por telefone.

        Args:
            phone: Telefone.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        return (
            self._db.query(CoreCustomer)
            .filter(
                CoreCustomer.phone == phone,
                CoreCustomer.company_id == company_id,
                CoreCustomer.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_company(
        self, company_id: int, active_only: bool = True
    ) -> List[CoreCustomer]:
        """
        Lista do tenant.

        Args:
            company_id: Tenant.
            active_only: Filtra ativos.

        Returns:
            Lista ordenada por nome.
        """
        q = self._db.query(CoreCustomer).filter(
            CoreCustomer.company_id == company_id,
            CoreCustomer.deleted_at.is_(None),
        )
        if active_only:
            q = q.filter(CoreCustomer.active.is_(True))
        return q.order_by(CoreCustomer.name).all()

    def save(self, customer: CoreCustomer) -> CoreCustomer:
        """
        Persiste customer.

        Args:
            customer: Entidade ORM.

        Returns:
            CoreCustomer com id.
        """
        self._db.add(customer)
        self._db.flush()
        self._db.refresh(customer)
        return customer
