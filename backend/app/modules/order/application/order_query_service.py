"""
Consultas read-only de Order genérico CoreFlow.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.order.domain.models import CoreOrder


class OrderQueryService:
    """
    Serviço de leitura para core_orders.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_orders(
        self,
        company_id: int,
        booking_id: Optional[int] = None,
        customer_id: Optional[int] = None,
    ) -> List[CoreOrder]:
        """
        Lista pedidos do tenant com filtros opcionais.

        Args:
            company_id: Tenant.
            booking_id: Filtra por booking core.
            customer_id: Filtra por cliente legado.

        Returns:
            Lista de CoreOrder.
        """
        query = self.db.query(CoreOrder).filter(
            CoreOrder.company_id == company_id,
            CoreOrder.deleted_at.is_(None),
        )
        if booking_id is not None:
            query = query.filter(CoreOrder.booking_id == booking_id)
        if customer_id is not None:
            query = query.filter(CoreOrder.customer_id == customer_id)
        return query.order_by(CoreOrder.created_at.desc()).all()

    def get_order(self, order_id: int, company_id: int) -> CoreOrder:
        """
        Obtém pedido por ID com escopo de tenant.

        Args:
            order_id: ID core_orders.
            company_id: Tenant.

        Returns:
            CoreOrder.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CoreOrder)
            .filter(
                CoreOrder.id == order_id,
                CoreOrder.company_id == company_id,
                CoreOrder.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Order", str(order_id))
        return row
