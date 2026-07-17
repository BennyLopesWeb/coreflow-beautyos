"""R2-F0.5 / R2-F1 / R3-F2 — ACL wiring e scheduling port."""
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import BusinessRuleError
from app.shared.acl.booking_port import LegacyBookingAdapter
from app.shared.acl.scheduling_port import LegacySchedulingPortAdapter

BOOKING_COMMANDS_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "modules"
    / "booking"
    / "application"
    / "commands"
)

FORBIDDEN_IMPORTS = (
    "ReservationService",
    "LegacySyncService",
    "from app.services.reservation_service",
    "from app.modules.catalog.application.legacy_sync_service",
)


def test_booking_commands_have_no_forbidden_imports():
    """FF-BKG-001/002 — commands não importam ReservationService nem LegacySyncService."""
    command_files = list(BOOKING_COMMANDS_DIR.glob("*.py"))
    assert command_files, "Nenhum command encontrado"
    violations = []
    for path in command_files:
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IMPORTS:
            if forbidden in text:
                violations.append(f"{path.name}: {forbidden}")
    assert not violations, "Imports proibidos em commands:\n" + "\n".join(violations)


def test_legacy_booking_adapter_approve_reject_removed(db, monkeypatch):
    """R3-F2 — approve/reject via_legacy nunca delegam a ReservationService; BusinessRuleError."""
    adapter = LegacyBookingAdapter(db)
    monkeypatch.setattr(adapter, "_track", lambda: None)

    approve_mock = MagicMock()
    reject_mock = MagicMock()
    monkeypatch.setattr(
        "app.services.reservation_service.ReservationService.aprovar",
        approve_mock,
    )
    monkeypatch.setattr(
        "app.services.reservation_service.ReservationService.rejeitar",
        reject_mock,
    )

    with pytest.raises(BusinessRuleError):
        adapter.approve_booking_via_legacy(42)
    approve_mock.assert_not_called()

    with pytest.raises(BusinessRuleError):
        adapter.reject_booking_via_legacy(42, "motivo teste")
    reject_mock.assert_not_called()

    sync_mock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.modules.catalog.application.legacy_sync_service.LegacySyncService.sync_booking_from_agendamento",
        sync_mock,
    )
    adapter.sync_booking_from_agendamento(99)
    sync_mock.assert_called_once()


def test_scheduling_port_adapter_delegates_disponibilidade(
    db, synced_catalog, monkeypatch
):
    """SchedulingPort ACL delega DisponibilidadeService (ADR-029)."""
    catalog, offering = synced_catalog
    adapter = LegacySchedulingPortAdapter(db)
    monkeypatch.setattr(adapter, "_track", lambda: None)

    starts = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(
        days=3
    )
    ends = starts + timedelta(minutes=60)

    mock_horario = MagicMock()
    mock_horario.horario = starts
    mock_horario.disponivel = True

    calc_mock = MagicMock(return_value=[mock_horario])
    monkeypatch.setattr(
        adapter._disponibilidade,
        "calcular_horarios_disponiveis",
        calc_mock,
    )
    monkeypatch.setattr(adapter._schedule, "tem_conflito", MagicMock(return_value=False))

    result = adapter.check_availability(
        company_id=catalog.company_id,
        resource_id=catalog.id,
        starts_at=starts,
        ends_at=ends,
        offering_id=offering.id,
        legacy_tranca_id=catalog.legacy_tranca_id,
        legacy_service_image_id=offering.legacy_service_image_id,
    )
    assert result is True
    calc_mock.assert_called_once()
