"""
Consultas read-only de Payment genérico CoreFlow.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.payments.domain.models import CorePayment


class PaymentQueryService:
    """
    Serviço de leitura para core_payments.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_by_booking(
        self, booking_id: int, company_id: int
    ) -> List[CorePayment]:
        """
        Lista pagamentos de um booking genérico.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            Lista de CorePayment.
        """
        return (
            self.db.query(CorePayment)
            .filter(
                CorePayment.booking_id == booking_id,
                CorePayment.company_id == company_id,
                CorePayment.deleted_at.is_(None),
            )
            .order_by(CorePayment.created_at.asc())
            .all()
        )

    def list_by_legacy_agendamento(
        self, agendamento_id: int, company_id: int
    ) -> List[CorePayment]:
        """
        Lista pagamentos por ID legado de agendamento.

        Args:
            agendamento_id: ID agendamentos.
            company_id: Tenant.

        Returns:
            Lista de CorePayment.
        """
        return (
            self.db.query(CorePayment)
            .filter(
                CorePayment.legacy_agendamento_id == agendamento_id,
                CorePayment.company_id == company_id,
                CorePayment.deleted_at.is_(None),
            )
            .order_by(CorePayment.created_at.asc())
            .all()
        )

    def get_payment(self, payment_id: int, company_id: int) -> CorePayment:
        """
        Obtém payment por ID com escopo de tenant.

        Args:
            payment_id: ID core_payments.
            company_id: Tenant.

        Returns:
            CorePayment.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CorePayment)
            .filter(
                CorePayment.id == payment_id,
                CorePayment.company_id == company_id,
                CorePayment.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Payment", str(payment_id))
        return row
