"""
CustomerQueryAdapter — valida cliente legado para booking create (R2-F3b).
"""
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.modules.customer.application.ports.customer_query_port import CustomerSnapshot
from app.modules.customer.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)


class SqlAlchemyCustomerQueryAdapter:
    """
    Implementação de ``CustomerQueryPort``.

    Lê ``clientes`` (FK de ``core_bookings.customer_id``) e enriquece com
    ``core_customers`` quando sincronizado.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._db = db
        self._repo = SqlAlchemyCustomerRepository(db)

    def get_customer(self, customer_id: int, company_id: int) -> CustomerSnapshot:
        """
        Carrega snapshot a partir do ID legado.

        Args:
            customer_id: ID ``clientes``.
            company_id: Tenant.

        Returns:
            CustomerSnapshot.

        Raises:
            ValueError: Cliente inexistente, deletado ou fora do tenant.
        """
        cliente = (
            self._db.query(Cliente)
            .filter(Cliente.id == customer_id, Cliente.deleted_at.is_(None))
            .first()
        )
        if not cliente:
            raise ValueError(f"Customer {customer_id} não encontrado")

        if cliente.company_id is not None and cliente.company_id != company_id:
            raise ValueError(f"Customer {customer_id} não pertence ao tenant")

        core = self._repo.get_by_legacy_id(customer_id, company_id)
        # Legado Cliente não tem flag ativo; soft-delete já filtrado. Core define active.
        active = bool(core.active) if core is not None else True

        return CustomerSnapshot(
            legacy_cliente_id=cliente.id,
            core_customer_id=core.id if core else None,
            company_id=company_id,
            name=cliente.nome or (core.name if core else ""),
            active=active,
            phone=cliente.telefone or (core.phone if core else ""),
        )
