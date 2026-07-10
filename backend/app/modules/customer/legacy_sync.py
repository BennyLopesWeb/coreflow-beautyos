"""
Sincronização Strangler Fig — ``clientes`` → ``core_customers``.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.cliente import Cliente
from app.modules.customer.models import CoreCustomer

logger = get_logger("customer_sync")


class CustomerLegacySyncService:
    """
    Sincroniza clientes legados para o metamodelo Customer.

    Idempotente — pode rodar no startup.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza todos os clientes ativos.

        Returns:
            Quantidade processada.
        """
        clientes = self.db.query(Cliente).filter(Cliente.deleted_at.is_(None)).all()
        count = 0
        for cliente in clientes:
            self._upsert(cliente)
            count += 1
        self.db.commit()
        logger.info(f"Sync customers: {count}")
        return count

    def sync_one(self, cliente_id: int) -> Optional[CoreCustomer]:
        """
        Sincroniza um cliente específico.

        Args:
            cliente_id: ID ``clientes``.

        Returns:
            CoreCustomer ou None.
        """
        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.deleted_at.is_(None))
            .first()
        )
        if not cliente:
            return None
        row = self._upsert(cliente)
        self.db.commit()
        return row

    def _upsert(self, cliente: Cliente) -> CoreCustomer:
        """
        Cria ou atualiza core_customer a partir de Cliente legado.

        Args:
            cliente: Registro legado.

        Returns:
            CoreCustomer persistido.
        """
        existing = (
            self.db.query(CoreCustomer)
            .filter(CoreCustomer.legacy_cliente_id == cliente.id)
            .first()
        )
        payload = dict(
            company_id=cliente.company_id or 1,
            name=cliente.nome,
            phone=cliente.telefone,
            email=cliente.email,
            active=True,
            plugin_metadata={"source": "beauty", "legacy": "Cliente"},
        )
        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing
        row = CoreCustomer(legacy_cliente_id=cliente.id, **payload)
        self.db.add(row)
        return row

    def resolve_legacy_id(self, core_customer_id: int) -> int:
        """
        Resolve ID genérico para ID legado ``clientes``.

        Args:
            core_customer_id: ID core_customers.

        Returns:
            ID clientes.

        Raises:
            ValueError: Se mapeamento ausente.
        """
        row = (
            self.db.query(CoreCustomer)
            .filter(CoreCustomer.id == core_customer_id)
            .first()
        )
        if not row or not row.legacy_cliente_id:
            raise ValueError(f"Customer {core_customer_id} sem mapeamento legado")
        return row.legacy_cliente_id
