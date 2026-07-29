"""
Helpers de ledger financeiro para testes (RECONCILE-DEPOSIT-SOURCES-01).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Union


def seed_ledger_deposit(
    db,
    booking_or_id: Union[int, object],
    valor: Optional[Decimal] = None,
):
    """
    Registra ``Payment`` PAID no ledger para testes de confirmação/ativação.

    ``confirmar_deposito_por_booking`` não faz upsert a partir de
    ``deposit_amount`` (cotação comercial). Testes que precisam ativar a
    reserva devem semear o ledger antes.

    Args:
        db: Sessão SQLAlchemy de teste.
        booking_or_id: ``CoreBooking`` ou ``booking_id``.
        valor: Valor pago; se omitido, usa ``deposit_amount`` do booking
            (ou R$ 100,00 se indisponível).

    Returns:
        ``Payment`` persistido com status PAID.
    """
    from app.models.payment import Payment, PaymentStatus, PaymentType
    from app.modules.booking.domain.models import CoreBooking

    if isinstance(booking_or_id, int):
        booking_id = booking_or_id
        booking = db.query(CoreBooking).filter(CoreBooking.id == booking_id).first()
    else:
        booking = booking_or_id
        booking_id = int(booking.id)

    if valor is None:
        if booking is not None and booking.deposit_amount is not None:
            valor = Decimal(str(booking.deposit_amount))
        else:
            valor = Decimal("100.00")

    pag = Payment(
        booking_id=booking_id,
        tipo=PaymentType.DEPOSIT,
        valor=valor,
        status=PaymentStatus.PAID,
        paid_at=datetime.utcnow(),
    )
    db.add(pag)
    db.commit()
    db.refresh(pag)
    return pag
