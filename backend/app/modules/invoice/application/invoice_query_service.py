"""
Consultas read-only de Invoice genérico CoreFlow.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.invoice.domain.models import CoreInvoice


class InvoiceQueryService:
    """
    Serviço de leitura para core_invoices.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_invoices(
        self,
        company_id: int,
        order_id: Optional[int] = None,
        booking_id: Optional[int] = None,
    ) -> List[CoreInvoice]:
        """
        Lista faturas do tenant com filtros opcionais.

        Args:
            company_id: Tenant.
            order_id: Filtra por pedido core.
            booking_id: Filtra por booking core.

        Returns:
            Lista de CoreInvoice.
        """
        query = self.db.query(CoreInvoice).filter(
            CoreInvoice.company_id == company_id,
            CoreInvoice.deleted_at.is_(None),
        )
        if order_id is not None:
            query = query.filter(CoreInvoice.order_id == order_id)
        if booking_id is not None:
            query = query.filter(CoreInvoice.booking_id == booking_id)
        return query.order_by(CoreInvoice.issued_at.desc()).all()

    def get_invoice(self, invoice_id: int, company_id: int) -> CoreInvoice:
        """
        Obtém fatura por ID com escopo de tenant.

        Args:
            invoice_id: ID core_invoices.
            company_id: Tenant.

        Returns:
            CoreInvoice.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CoreInvoice)
            .filter(
                CoreInvoice.id == invoice_id,
                CoreInvoice.company_id == company_id,
                CoreInvoice.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Invoice", str(invoice_id))
        return row
