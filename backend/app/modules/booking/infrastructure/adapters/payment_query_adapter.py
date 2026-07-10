"""
ACL adapter — PaymentQueryPort via legado (ADR-028).
"""
from sqlalchemy.orm import Session

from app.modules.booking.domain.models import CoreBooking
from app.models.agendamento import Agendamento, ReservationStatus


class LegacyPaymentQueryAdapter:
    """
    Implementa PaymentQueryPort consultando agendamento legado via FK.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def is_deposit_confirmed(self, booking_id: int, company_id: int) -> bool:
        """
        Verifica sinal pago no agendamento projetado.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            True se sinal confirmado ou status aguardando aprovação.
        """
        row = (
            self.db.query(CoreBooking)
            .filter(
                CoreBooking.id == booking_id,
                CoreBooking.company_id == company_id,
                CoreBooking.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            return False
        if row.deposit_paid:
            return True
        if not row.legacy_agendamento_id:
            return False
        ag = (
            self.db.query(Agendamento)
            .filter(Agendamento.id == row.legacy_agendamento_id)
            .first()
        )
        if not ag:
            return False
        if ag.sinal_pago:
            return True
        return ag.status in (
            ReservationStatus.PENDING_APPROVAL,
            ReservationStatus.WAITING_TIME_CONFIRMATION,
        )
