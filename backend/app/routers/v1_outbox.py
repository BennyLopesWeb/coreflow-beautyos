"""
Router API v1 — Outbox admin (replay/worker CF-13).
"""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.identity.api.deps import get_current_admin_user
from app.models.user import User
from app.shared.events.outbox import CoreEventOutbox, OutboxService, OutboxStatus

router = APIRouter(prefix="/v1/outbox", tags=["CoreFlow — Outbox"])


class OutboxPendingResponse(BaseModel):
    """
    Resumo de eventos pendentes no outbox.

    Attributes:
        pending_count: Quantidade de eventos pending.
        failed_count: Quantidade de eventos failed.
    """

    pending_count: int
    failed_count: int


class OutboxReplayResponse(BaseModel):
    """
    Resultado de replay manual do outbox.

    Attributes:
        processed: Eventos processados com sucesso.
    """

    processed: int


@router.get("/status", response_model=OutboxPendingResponse)
def outbox_status(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Retorna contagem de eventos pending/failed no outbox.

    Returns:
        Contagens para monitoramento admin.
    """
    pending = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.status == OutboxStatus.PENDING)
        .count()
    )
    failed = (
        db.query(CoreEventOutbox)
        .filter(CoreEventOutbox.status == OutboxStatus.FAILED)
        .count()
    )
    return OutboxPendingResponse(pending_count=pending, failed_count=failed)


@router.post("/replay", response_model=OutboxReplayResponse)
def outbox_replay(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """
    Reprocessa eventos pendentes do outbox (modo poll manual).

    Returns:
        Quantidade processada.
    """
    processed = OutboxService(db).replay_pending()
    return OutboxReplayResponse(processed=processed)
