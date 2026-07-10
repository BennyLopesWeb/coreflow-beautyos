"""Testes CF-13 — Expo Push API, universal links, outbox worker RabbitMQ."""
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.integrations.expo_push import ExpoPushClient
from app.modules.push.application.deep_link_service import DeepLinkService
from app.shared.events.domain_event import DomainEvent
from app.shared.events.outbox import OutboxService, OutboxStatus


def test_universal_link_build(default_company):
    """Universal link HTTPS inclui host, tenant e path."""
    url = DeepLinkService().build_universal(
        default_company.slug,
        "beauty",
        "booking_detail",
        booking_id=42,
    )
    assert url == f"https://app.coreflow.app/{default_company.slug}/bookings/42"


def test_build_pair_includes_both_links(default_company):
    """build_pair retorna deep_link e universal_link."""
    pair = DeepLinkService().build_pair(
        default_company.slug,
        "beauty",
        "booking_detail",
        booking_id=1,
    )
    assert pair["deep_link"].startswith("trancapro://")
    assert pair["universal_link"].startswith("https://app.coreflow.app/")


def test_plugin_config_includes_universal_host(client, default_company):
    """Config plugin expõe universal_host para App Links."""
    response = client.get(f"/v1/plugins/config/by-company/{default_company.slug}")
    assert response.status_code == 200
    assert response.json()["deep_links"]["universal_host"] == "app.coreflow.app"


def test_expo_push_mock_when_not_live():
    """Sem EXPO_PUSH_LIVE, cliente usa mock local."""
    client = ExpoPushClient(access_token=None)
    result = client.send(
        "ExponentPushToken[dev-user-1]",
        "Teste",
        "Corpo",
        {"deep_link": "trancapro://demo/bookings/1"},
    )
    assert result["status"] == "mock"


@patch("app.integrations.expo_push.httpx.post")
def test_expo_push_live_api(mock_post, monkeypatch):
    """Com EXPO_PUSH_LIVE, chama API Expo Push."""
    monkeypatch.setattr(settings, "EXPO_PUSH_LIVE", True)
    monkeypatch.setattr(settings, "PUSH_NOTIFICATIONS_ENABLED", True)
    monkeypatch.setattr(settings, "EXPO_PUSH_ACCESS_TOKEN", "test-token")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"data": [{"status": "ok"}]}
    mock_post.return_value = mock_response

    client = ExpoPushClient(access_token="test-token")
    result = client.send(
        "ExponentPushToken[real-device-token]",
        "Aprovado",
        "Sua reserva foi aprovada",
        {"universal_link": "https://app.coreflow.app/demo/bookings/1"},
    )

    assert result["status"] == "enviada"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["to"] == "ExponentPushToken[real-device-token]"


def test_outbox_deferred_mode(db, monkeypatch):
    """OUTBOX_DISPATCH_MODE=deferred persiste pending sem publicar."""
    monkeypatch.setattr(settings, "OUTBOX_DISPATCH_MODE", "deferred")

    event = DomainEvent(
        event_type="booking.created",
        company_id=1,
        payload={"booking_id": 1},
    )
    row = OutboxService(db).record_and_publish(event)
    db.commit()

    assert row.status == OutboxStatus.PENDING


def test_outbox_replay_processes_deferred(db, monkeypatch):
    """replay_pending processa eventos deferred."""
    monkeypatch.setattr(settings, "OUTBOX_DISPATCH_MODE", "deferred")

    event = DomainEvent(
        event_type="booking.created",
        company_id=1,
        payload={"booking_id": 2},
    )
    OutboxService(db).record_and_publish(event)
    db.commit()

    processed = OutboxService(db).replay_pending()
    assert processed == 1


def test_outbox_rabbitmq_mode_publishes_without_sync_bus(db, monkeypatch):
    """Modo rabbitmq enfileira sem marcar processed imediatamente."""
    monkeypatch.setattr(settings, "OUTBOX_DISPATCH_MODE", "rabbitmq")
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", True)

    mock_adapter = MagicMock()
    with patch(
        "app.shared.events.rabbitmq_adapter.get_rabbitmq_adapter",
        return_value=mock_adapter,
    ):
        event = DomainEvent(
            event_type="booking.approved",
            company_id=1,
            payload={"booking_id": 3},
        )
        row = OutboxService(db).record_and_publish(event)
        db.commit()

    assert row.status == OutboxStatus.PENDING
    mock_adapter.publish.assert_called_once()


def test_outbox_status_and_replay_api(client, admin_headers, db, monkeypatch):
    """Admin pode consultar status e disparar replay manual."""
    monkeypatch.setattr(settings, "OUTBOX_DISPATCH_MODE", "deferred")
    event = DomainEvent(
        event_type="booking.created",
        company_id=1,
        payload={"booking_id": 9},
    )
    OutboxService(db).record_and_publish(event)
    db.commit()

    status_resp = client.get("/v1/outbox/status", headers=admin_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["pending_count"] >= 1

    replay_resp = client.post("/v1/outbox/replay", headers=admin_headers)
    assert replay_resp.status_code == 200
    assert replay_resp.json()["processed"] >= 1
