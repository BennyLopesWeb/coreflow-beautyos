"""
Router de pagamentos persistidos (deposit + final).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.dependencies import get_current_admin_user as get_current_admin
from app.models.user import User
from app.schemas.payment_reservation import (
    DepositPaymentRequest,
    FinalPaymentRequest,
    PaymentResponse,
)
from app.services.payment_reservation_service import PaymentReservationService
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/payments", tags=["Pagamentos"])


@router.post("/deposit", response_model=PaymentResponse)
def confirmar_deposito(
    body: DepositPaymentRequest,
    db: Session = Depends(get_db),
):
    """
    Confirma pagamento do sinal (persistido em payments).
    Status reserva: PENDING_PAYMENT → PENDING_APPROVAL.
    """
    svc = PaymentReservationService(db)
    try:
        pag = svc.confirmar_deposito(
            body.agendamento_id,
            body.transaction_id,
            body.comprovante_url,
        )
        return PaymentResponse.model_validate(pag)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deposit/admin", response_model=PaymentResponse)
def confirmar_deposito_admin(
    body: DepositPaymentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin confirma sinal recebido."""
    return confirmar_deposito(body, db)


@router.post("/final", response_model=PaymentResponse)
def confirmar_pagamento_final(
    body: FinalPaymentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Confirma pagamento final (remainingAmount).
    Status reserva: COMPLETED → PAID.
    """
    svc = ReservationService(db)
    try:
        ag = svc.registrar_pagamento_final(body.agendamento_id, body.transaction_id)
        pagamentos = PaymentReservationService(db).listar_por_reserva(ag.id)
        final = [p for p in pagamentos if p.tipo.value in ("final_payment", "final")]
        if not final:
            raise HTTPException(status_code=500, detail="Pagamento final não registrado")
        return PaymentResponse.model_validate(final[-1])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reservation/{reservation_id}", response_model=List[PaymentResponse])
def listar_pagamentos_reserva(reservation_id: int, db: Session = Depends(get_db)):
    """Lista pagamentos de uma reserva."""
    pags = PaymentReservationService(db).listar_por_reserva(reservation_id)
    return [PaymentResponse.model_validate(p) for p in pags]
