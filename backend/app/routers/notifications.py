"""
Router de Notificações
Endpoints para gerenciamento de notificações
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notificações"])


@router.post("/enviar-lembretes")
def enviar_lembretes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Envia lembretes pendentes para agendamentos próximos
    Executar periodicamente (cron job)
    Requer autenticação
    """
    service = NotificationService(db)
    try:
        logs = service.enviar_lembretes_pendentes()
        return {
            "enviadas": len([l for l in logs if l.status.value == "enviada"]),
            "falhas": len([l for l in logs if l.status.value == "falha"]),
            "total": len(logs)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

