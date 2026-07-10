"""Testes CF-12 — deep links, push via outbox, production enforcement block."""
from app.core.core_enforcement import resolve_enforcement_mode
from app.core.config import settings
from app.models.notification_log import NotificationLog, NotificationType
from app.modules.push.application.deep_link_service import DeepLinkService
from app.modules.push.application.push_service import PushNotificationService
from app.modules.push.domain.models import CoreDeviceToken, DevicePlatform
from app.shared.events.domain_event import DomainEvent


def test_deep_link_build_beauty(default_company):
    """Deep link beauty inclui tenant slug e booking id."""
    url = DeepLinkService().build(
        default_company.slug,
        "beauty",
        "booking_detail",
        booking_id=42,
    )
    assert url == f"trancapro://{default_company.slug}/bookings/42"


def test_deep_link_build_sports(default_company):
    """Plugin sports usa rota /reservas no manifest."""
    url = DeepLinkService().build(
        default_company.slug,
        "sports",
        "booking_detail",
        booking_id=7,
    )
    assert url == f"trancapro://{default_company.slug}/reservas/7"


def test_plugin_config_includes_deep_links(client, default_company):
    """GET plugin config expõe deep_links para o frontend."""
    response = client.get(f"/v1/plugins/config/by-company/{default_company.slug}")
    assert response.status_code == 200
    body = response.json()
    assert "deep_links" in body
    assert body["deep_links"]["scheme"] == "trancapro"
    assert "booking_detail" in body["deep_links"]["routes"]


def test_device_register(client, admin_headers, admin_user, db, default_company):
    """POST /v1/devices/register persiste token Expo Push."""
    response = client.post(
        "/v1/devices/register",
        json={
            "expo_push_token": "ExponentPushToken[test-cf12-admin]",
            "platform": "android",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["expo_push_token"] == "ExponentPushToken[test-cf12-admin]"

    token = (
        db.query(CoreDeviceToken)
        .filter(CoreDeviceToken.expo_push_token == "ExponentPushToken[test-cf12-admin]")
        .first()
    )
    assert token is not None
    assert token.company_id == default_company.id
    assert token.user_id == admin_user.id


def test_push_on_booking_approved_event(db, default_company, admin_user):
    """Evento booking.approved gera NotificationLog PUSH com deep link."""
    PushNotificationService(db).register_device(
        company_id=default_company.id,
        user_id=admin_user.id,
        expo_push_token="ExponentPushToken[test-push-event]",
        platform=DevicePlatform.ANDROID,
    )

    event = DomainEvent(
        event_type="booking.approved",
        company_id=default_company.id,
        payload={"booking_id": 99, "legacy_agendamento_id": 99},
    )
    logs = PushNotificationService(db).handle_domain_event(event)

    assert len(logs) == 1
    assert logs[0].tipo == NotificationType.PUSH
    assert f"/bookings/99" in logs[0].mensagem

    stored = db.query(NotificationLog).filter(NotificationLog.id == logs[0].id).first()
    assert stored is not None
    assert stored.tipo == NotificationType.PUSH


def test_production_enforcement_defaults_block(monkeypatch):
    """APP_ENV=production força enforcement block (fase final CF-12)."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert resolve_enforcement_mode() == "block"


def test_production_enforcement_warn_override(monkeypatch):
    """CORE_ENFORCEMENT_MODE=warn permite rollout gradual em production."""
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "CORE_ENFORCEMENT_MODE", "warn")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert resolve_enforcement_mode() == "warn"
