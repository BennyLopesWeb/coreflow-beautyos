"""Testes CF-14 — well-known hosting, Kafka adapter, mobile preview."""
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.modules.mobile.application.well_known_service import WellKnownService
from app.shared.events.domain_event import DomainEvent
from app.shared.events.outbox import OutboxService, OutboxStatus


def test_apple_app_site_association_structure():
    """AASA contém applinks com appID e paths."""
    body = WellKnownService().apple_app_site_association()
    assert "applinks" in body
    assert body["applinks"]["details"][0]["appID"] == settings.MOBILE_IOS_APP_ID
    assert "/*" in body["applinks"]["details"][0]["paths"]


def test_android_asset_links_structure():
    """assetlinks.json contém package e fingerprints."""
    body = WellKnownService().android_asset_links()
    assert body[0]["target"]["package_name"] == settings.MOBILE_ANDROID_PACKAGE
    assert len(body[0]["target"]["sha256_cert_fingerprints"]) >= 1


def test_well_known_endpoints(client):
    """Rotas .well-known retornam JSON application/json."""
    aasa = client.get("/.well-known/apple-app-site-association")
    assert aasa.status_code == 200
    assert aasa.headers["content-type"].startswith("application/json")
    assert "applinks" in aasa.json()

    asset = client.get("/.well-known/assetlinks.json")
    assert asset.status_code == 200
    assert asset.headers["content-type"].startswith("application/json")
    assert isinstance(asset.json(), list)


def test_mobile_well_known_preview(client):
    """GET /v1/mobile/well-known/preview expõe URLs de verificação."""
    response = client.get("/v1/mobile/well-known/preview")
    assert response.status_code == 200
    body = response.json()
    assert body["universal_link_host"] == settings.MOBILE_UNIVERSAL_LINK_HOST
    assert "apple-app-site-association" in body["endpoints"]["apple_app_site_association"]


def test_outbox_kafka_mode_publishes_without_sync_bus(db, monkeypatch):
    """Modo kafka enfileira sem marcar processed imediatamente."""
    monkeypatch.setattr(settings, "OUTBOX_DISPATCH_MODE", "kafka")
    monkeypatch.setattr(settings, "KAFKA_ENABLED", True)

    mock_adapter = MagicMock()
    with patch(
        "app.shared.events.kafka_adapter.get_kafka_adapter",
        return_value=mock_adapter,
    ):
        event = DomainEvent(
            event_type="booking.approved",
            company_id=1,
            payload={"booking_id": 5},
        )
        row = OutboxService(db).record_and_publish(event)
        db.commit()

    assert row.status == OutboxStatus.PENDING
    mock_adapter.publish.assert_called_once()


@patch("app.shared.events.kafka_adapter.KafkaEventAdapter._get_producer")
def test_kafka_adapter_publish(mock_producer_factory, monkeypatch):
    """KafkaEventAdapter serializa evento e publica no tópico."""
    monkeypatch.setattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    monkeypatch.setattr(settings, "KAFKA_TOPIC", "coreflow.events")
    monkeypatch.setattr(settings, "KAFKA_SCHEMA_REGISTRY_ENABLED", False)

    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_producer.send.return_value = mock_future
    mock_producer_factory.return_value = mock_producer

    from app.shared.events.kafka_adapter import KafkaEventAdapter

    adapter = KafkaEventAdapter()
    event = DomainEvent(
        event_type="booking.created",
        company_id=1,
        payload={"booking_id": 1},
    )
    adapter.publish(event, outbox_id=10)

    mock_producer.send.assert_called_once()
    sent_payload = mock_producer.send.call_args[0][1]
    assert sent_payload["outbox_id"] == 10
    assert sent_payload["event"]["event_type"] == "booking.created"
    adapter.close()
