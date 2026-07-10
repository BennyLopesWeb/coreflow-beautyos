"""
Queries de booking — camada CQRS (leitura).
"""
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.booking.domain.models import CoreBooking
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.core.exceptions import NotFoundError


class BookingQueryService:
    """
    Consultas read-only sobre bookings genéricos.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_bookings(
        self,
        company_id: int,
        customer_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[CoreBooking]:
        """
        Lista bookings do tenant.

        Args:
            company_id: ID da empresa.
            customer_id: Filtrar por cliente.
            limit: Máximo de registros.

        Returns:
            Lista de CoreBooking.
        """
        q = (
            self.db.query(CoreBooking)
            .options(
                joinedload(CoreBooking.catalog),
                joinedload(CoreBooking.offering),
            )
            .filter(
                CoreBooking.company_id == company_id,
                CoreBooking.deleted_at.is_(None),
            )
        )
        if customer_id:
            q = q.filter(CoreBooking.customer_id == customer_id)
        return q.order_by(CoreBooking.created_at.desc()).limit(limit).all()

    def get_booking(self, booking_id: int, company_id: Optional[int] = None) -> CoreBooking:
        """
        Obtém booking por ID.

        Args:
            booking_id: ID core_bookings.
            company_id: Filtrar tenant.

        Returns:
            CoreBooking.

        Raises:
            NotFoundError: Se não existir.
        """
        q = (
            self.db.query(CoreBooking)
            .options(
                joinedload(CoreBooking.catalog),
                joinedload(CoreBooking.offering),
            )
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.deleted_at.is_(None),
            )
        )
        if company_id is not None:
            q = q.filter(CoreBooking.company_id == company_id)
        row = q.first()
        if not row:
            raise NotFoundError("Booking", str(booking_id))
        return row
