"""
Router API v1 — Device tokens (push mobile CF-12).
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.identity.api.deps import get_current_active_user, get_tenant_context
from app.models.user import User
from app.modules.push.application.push_service import PushNotificationService
from app.modules.push.domain.models import DevicePlatform
from app.shared.kernel.tenant import TenantContext

router = APIRouter(prefix="/v1/devices", tags=["CoreFlow — Devices"])


class DeviceRegisterRequest(BaseModel):
    """
    Body para registro de token Expo Push.

    Attributes:
        expo_push_token: Token retornado pelo Expo Notifications.
        platform: Plataforma do dispositivo (ios, android, web).
    """

    expo_push_token: str = Field(..., min_length=8)
    platform: DevicePlatform = DevicePlatform.ANDROID


class DeviceRegisterResponse(BaseModel):
    """
    Resposta do registro de dispositivo.

    Attributes:
        id: ID do registro core_device_tokens.
        expo_push_token: Token registrado.
        platform: Plataforma informada.
        active: Se o token está ativo.
    """

    id: int
    expo_push_token: str
    platform: DevicePlatform
    active: bool


@router.post("/register", response_model=DeviceRegisterResponse)
def registrar_dispositivo(
    body: DeviceRegisterRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Registra token Expo Push do usuário autenticado no tenant atual.

    Args:
        body: Token e plataforma do dispositivo.

    Returns:
        Confirmação do registro.
    """
    token = PushNotificationService(db).register_device(
        company_id=tenant.company_id,
        user_id=current_user.id,
        expo_push_token=body.expo_push_token,
        platform=body.platform,
    )
    return DeviceRegisterResponse(
        id=token.id,
        expo_push_token=token.expo_push_token,
        platform=token.platform,
        active=token.active,
    )
