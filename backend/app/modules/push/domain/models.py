"""
Entidade ORM CoreDeviceToken — tokens Expo Push por tenant/usuário.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class DevicePlatform(str, enum.Enum):
    """Plataforma do dispositivo mobile."""

    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class CoreDeviceToken(Base):
    """
    Token de push mobile registrado por usuário/tenant.

    Usado pelo PushNotificationService para enviar notificações
    disparadas por eventos do outbox (booking.approved, etc.).

    Attributes:
        id: PK.
        company_id: Tenant CoreFlow.
        user_id: Usuário autenticado que registrou o token.
        expo_push_token: Token Expo Push (ExponentPushToken[...]).
        platform: ios | android | web.
        active: Se o token ainda é válido.
    """

    __tablename__ = "core_device_tokens"
    __table_args__ = (
        UniqueConstraint("expo_push_token", name="uq_core_device_tokens_expo_push_token"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expo_push_token = Column(String(255), nullable=False)
    platform = Column(enum_values(DevicePlatform), nullable=False, default=DevicePlatform.ANDROID)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
