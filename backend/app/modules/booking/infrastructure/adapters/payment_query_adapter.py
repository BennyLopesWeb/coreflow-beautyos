"""
ACL adapter — PaymentQueryPort via legado (ADR-028).

.. deprecated:: 2.11.0-r4-f8
    A verificação via ``Agendamento.sinal_pago``/``Agendamento.status``
    (fallback para bookings com ``legacy_agendamento_id`` preenchido,
    histórico de dual-write anterior a R4-F3) foi removida junto com o
    DROP físico da tabela ``agendamentos`` (ADR-024 sunset / RFC-003
    M11+) — ``CoreBooking.deposit_paid`` (atualizado diretamente por
    ``PaymentReservationService.confirmar_deposito_por_booking``) já é a
    fonte da verdade única desde R4-F6.
"""
from sqlalchemy.orm import Session

from app.modules.booking.domain.models import CoreBooking


class LegacyPaymentQueryAdapter:
    """
    Implementa PaymentQueryPort consultando ``CoreBooking.deposit_paid``.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def is_deposit_confirmed(self, booking_id: int, company_id: int) -> bool:
        """
        Verifica sinal pago no booking.

        .. deprecated:: 2.11.0-r4-f8
            Não há mais fallback a ``Agendamento`` legado (tabela
            removida) — consulta exclusivamente ``CoreBooking.deposit_paid``.

        Args:
            booking_id: ID core_bookings.
            company_id: Tenant.

        Returns:
            True se ``CoreBooking.deposit_paid`` estiver marcado.
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
        return bool(row.deposit_paid)
