"""
R3-F2 — Remoção do booking write path legado (ADR-027/ADR-033/RFC-003 M4).

Cobre:
    - ``ReservationService`` métodos de escrita (criar/criar_de_schema/
      aprovar/rejeitar/cancelar) sempre levantam ``BusinessRuleError``.
    - ``LegacyBookingAdapter.*_via_legacy`` nunca delegam a
      ``ReservationService`` — sempre levantam ``BusinessRuleError``.
    - ``CreateBookingHandler`` com flag ON continua funcional (smoke) e
      não publica mais o alias ``reservation.created`` no outbox.
    - ``FEATURE_BOOKING_CORE_ENABLED`` default ``True`` (kill-switch, sem
      fallback legado quando OFF).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.core.exceptions import BusinessRuleError
from app.core.feature_flags import feature_flags
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.events.outbox import CoreEventOutbox


def test_feature_booking_core_enabled_default_true():
    """R3-F2 — flag ``booking.core.enabled`` é True por padrão."""
    assert settings.FEATURE_BOOKING_CORE_ENABLED is True
    assert feature_flags.all_flags()["booking.core.enabled"]["enabled"] is True


def test_app_version_semver_major_2():
    """APP_VERSION permanece na linha 2.x após R3-F2 (release pin fica no gate F3+)."""
    assert settings.APP_VERSION.startswith("2.")


class TestReservationServiceWritesRemoved:
    """``ReservationService`` — métodos de escrita removidos (fail-fast)."""

    def test_criar_raises(self, db):
        """``criar`` sempre levanta ``BusinessRuleError``."""
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError):
            svc.criar(
                cliente_id=1,
                tranca_id=1,
                service_image_id=1,
                data_hora=datetime.now() + timedelta(days=1),
            )

    def test_criar_de_schema_raises(self, db):
        """``criar_de_schema`` sempre levanta ``BusinessRuleError``."""
        from app.schemas.reservation import ReservationCreate
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError):
            svc.criar_de_schema(
                ReservationCreate(
                    cliente_id=1,
                    tranca_id=1,
                    service_image_id=1,
                    data_hora=datetime.now() + timedelta(days=1),
                )
            )

    def test_aprovar_raises(self, db):
        """``aprovar`` sempre levanta ``BusinessRuleError`` — sem consultar DB."""
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError):
            svc.aprovar(999)

    def test_rejeitar_raises(self, db):
        """``rejeitar`` sempre levanta ``BusinessRuleError`` — sem consultar DB."""
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError):
            svc.rejeitar(999, "motivo qualquer")

    def test_cancelar_raises(self, db):
        """``cancelar`` sempre levanta ``BusinessRuleError`` — sem consultar DB."""
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError):
            svc.cancelar(999, "motivo qualquer")

    def test_error_message_points_to_v1_bookings(self, db):
        """Mensagem de erro referencia ``/v1/bookings`` para o novo path."""
        from app.services.reservation_service import ReservationService

        svc = ReservationService(db)
        with pytest.raises(BusinessRuleError) as excinfo:
            svc.cancelar(999)
        assert "/v1/bookings" in str(excinfo.value.detail)


class TestLegacyBookingAdapterViaLegacyRemoved:
    """``LegacyBookingAdapter.*_via_legacy`` — nunca delegam ao legado."""

    def test_create_via_legacy_never_calls_reservation_service(self, db, monkeypatch):
        """``create_booking_via_legacy`` não chama ``ReservationService`` e falha."""
        adapter = LegacyBookingAdapter(db)
        mock_criar = MagicMock()
        monkeypatch.setattr(
            "app.services.reservation_service.ReservationService.criar_de_schema",
            mock_criar,
        )
        with pytest.raises(BusinessRuleError):
            adapter.create_booking_via_legacy(
                customer_id=1,
                tranca_id=1,
                service_image_id=1,
                scheduled_at=datetime.now() + timedelta(days=1),
                company_id=1,
            )
        mock_criar.assert_not_called()

    def test_approve_via_legacy_never_calls_reservation_service(self, db, monkeypatch):
        """``approve_booking_via_legacy`` não chama ``ReservationService`` e falha."""
        adapter = LegacyBookingAdapter(db)
        mock_aprovar = MagicMock()
        monkeypatch.setattr(
            "app.services.reservation_service.ReservationService.aprovar",
            mock_aprovar,
        )
        with pytest.raises(BusinessRuleError):
            adapter.approve_booking_via_legacy(1)
        mock_aprovar.assert_not_called()

    def test_reject_via_legacy_never_calls_reservation_service(self, db, monkeypatch):
        """``reject_booking_via_legacy`` não chama ``ReservationService`` e falha."""
        adapter = LegacyBookingAdapter(db)
        mock_rejeitar = MagicMock()
        monkeypatch.setattr(
            "app.services.reservation_service.ReservationService.rejeitar",
            mock_rejeitar,
        )
        with pytest.raises(BusinessRuleError):
            adapter.reject_booking_via_legacy(1, "motivo")
        mock_rejeitar.assert_not_called()

    def test_cancel_via_legacy_never_calls_reservation_service(self, db, monkeypatch):
        """``cancel_booking_via_legacy`` não chama ``ReservationService`` e falha."""
        adapter = LegacyBookingAdapter(db)
        mock_cancelar = MagicMock()
        monkeypatch.setattr(
            "app.services.reservation_service.ReservationService.cancelar",
            mock_cancelar,
        )
        with pytest.raises(BusinessRuleError):
            adapter.cancel_booking_via_legacy(1, "motivo")
        mock_cancelar.assert_not_called()

    def test_via_legacy_error_message_points_to_v1_bookings(self, db):
        """Mensagem padronizada referencia ``/v1/bookings``."""
        adapter = LegacyBookingAdapter(db)
        with pytest.raises(BusinessRuleError) as excinfo:
            adapter.create_booking_via_legacy(
                customer_id=1,
                tranca_id=1,
                service_image_id=1,
                scheduled_at=datetime.now() + timedelta(days=1),
                company_id=1,
            )
        assert "/v1/bookings" in str(excinfo.value.detail)
        assert "R3-F2" in str(excinfo.value.detail)


class TestCommandsFailFastWhenFlagOff:
    """Commands de booking — fail-fast (sem legacy fallback) quando flag OFF."""

    def test_create_booking_handler_flag_off_raises(self, db, monkeypatch):
        """``CreateBookingHandler.execute`` levanta ``BusinessRuleError`` com flag OFF."""
        from app.modules.booking.application.commands.create_booking import (
            CreateBookingCommand,
            CreateBookingHandler,
        )

        monkeypatch.setattr(
            "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
            lambda key: False,
        )
        handler = CreateBookingHandler(db)
        with pytest.raises(BusinessRuleError):
            handler.execute(
                CreateBookingCommand(
                    customer_id=1,
                    catalog_id=1,
                    offering_id=1,
                    scheduled_at=datetime.now() + timedelta(days=1),
                    company_id=1,
                )
            )

    def test_approve_booking_handler_flag_off_raises(self, db, monkeypatch):
        """``ApproveBookingHandler.execute`` levanta ``BusinessRuleError`` com flag OFF."""
        from app.modules.booking.application.commands.approve_booking import (
            ApproveBookingCommand,
            ApproveBookingHandler,
        )

        monkeypatch.setattr(
            "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
            lambda key: False,
        )
        handler = ApproveBookingHandler(db)
        with pytest.raises(BusinessRuleError):
            handler.execute(ApproveBookingCommand(booking_id=1, company_id=1))

    def test_reject_booking_handler_flag_off_raises(self, db, monkeypatch):
        """``RejectBookingHandler.execute`` levanta ``BusinessRuleError`` com flag OFF."""
        from app.modules.booking.application.commands.reject_booking import (
            RejectBookingCommand,
            RejectBookingHandler,
        )

        monkeypatch.setattr(
            "app.modules.booking.application.commands.reject_booking.feature_flags.is_enabled",
            lambda key: False,
        )
        handler = RejectBookingHandler(db)
        with pytest.raises(BusinessRuleError):
            handler.execute(RejectBookingCommand(booking_id=1, company_id=1, reason="x"))

    def test_cancel_booking_handler_flag_off_raises(self, db, monkeypatch):
        """``CancelBookingHandler.execute`` levanta ``BusinessRuleError`` com flag OFF."""
        from app.modules.booking.application.commands.cancel_booking import (
            CancelBookingCommand,
            CancelBookingHandler,
        )

        monkeypatch.setattr(
            "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
            lambda key: False,
        )
        handler = CancelBookingHandler(db)
        with pytest.raises(BusinessRuleError):
            handler.execute(CancelBookingCommand(booking_id=1, company_id=1))


class TestCoreBookingNoAliasPublish:
    """Path core (flag ON) — smoke create + ausência do alias ``reservation.created``."""

    def test_create_booking_core_path_smoke_no_alias(
        self, client, db, synced_catalog, cliente_exemplo, booking_headers
    ):
        """Create via ``/v1/bookings`` (flag ON default) publica só ``booking.created``."""
        from app.services.disponibilidade_service import DisponibilidadeService

        catalog, offering = synced_catalog
        horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
            datetime.now() + timedelta(days=10),
            catalog.legacy_tranca_id,
            offering.legacy_service_image_id,
        )
        slot = next(h for h in horarios if h.disponivel)

        response = client.post(
            "/v1/bookings",
            json={
                "customer_id": cliente_exemplo.id,
                "catalog_id": catalog.id,
                "offering_id": offering.id,
                "scheduled_at": slot.horario.isoformat(),
            },
            headers=booking_headers(),
        )
        assert response.status_code == 201, response.text
        body = response.json()

        booking_evt = (
            db.query(CoreEventOutbox)
            .filter(
                CoreEventOutbox.event_type == "booking.created",
                CoreEventOutbox.aggregate_id == str(body["id"]),
            )
            .first()
        )
        alias_evt = (
            db.query(CoreEventOutbox)
            .filter(
                CoreEventOutbox.event_type == "reservation.created",
                CoreEventOutbox.aggregate_id == str(body["id"]),
            )
            .first()
        )
        assert booking_evt is not None
        assert alias_evt is None
