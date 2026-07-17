"""
ACL — LegacyCustomerPort (ADR-030 / R2-F3b).

Traduz sync legado ↔ metamodelo Customer sem regras de negócio.
"""
from typing import Optional, Protocol

from sqlalchemy.orm import Session

from app.modules.customer.legacy_sync import CustomerLegacySyncService
from app.modules.customer.models import CoreCustomer
from app.modules.customer.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)


class LegacyCustomerPort(Protocol):
    """
    Port ACL para sincronização Customer ↔ ``clientes``.
    """

    def sync_all(self) -> int:
        """
        Sincroniza todos os clientes ativos.

        Returns:
            Quantidade processada.
        """
        ...

    def sync_one(self, legacy_cliente_id: int) -> Optional[CoreCustomer]:
        """
        Sincroniza um cliente específico.

        Args:
            legacy_cliente_id: ID ``clientes``.

        Returns:
            CoreCustomer ou None.
        """
        ...

    def resolve_by_legacy_id(
        self, legacy_cliente_id: int, company_id: int
    ) -> Optional[CoreCustomer]:
        """
        Resolve metamodelo a partir do ID legado.

        Args:
            legacy_cliente_id: ID ``clientes``.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        ...


class LegacyCustomerAdapter:
    """
    Adapter ACL — encapsula ``CustomerLegacySyncService`` + repository.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self._sync = CustomerLegacySyncService(db)
        self._repo = SqlAlchemyCustomerRepository(db)

    def sync_all(self) -> int:
        """
        Delega sync completo.

        Returns:
            Quantidade processada.
        """
        return self._sync.sync_all()

    def sync_one(self, legacy_cliente_id: int) -> Optional[CoreCustomer]:
        """
        Delega sync de um cliente.

        Args:
            legacy_cliente_id: ID ``clientes``.

        Returns:
            CoreCustomer ou None.
        """
        return self._sync.sync_one(legacy_cliente_id)

    def resolve_by_legacy_id(
        self, legacy_cliente_id: int, company_id: int
    ) -> Optional[CoreCustomer]:
        """
        Resolve via repository.

        Args:
            legacy_cliente_id: ID ``clientes``.
            company_id: Tenant.

        Returns:
            CoreCustomer ou None.
        """
        return self._repo.get_by_legacy_id(legacy_cliente_id, company_id)
