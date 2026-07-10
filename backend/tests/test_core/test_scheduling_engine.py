"""Testes Scheduling Engine + Resource Conflict (CF-4)."""
from datetime import datetime, timedelta

import pytest

from app.modules.scheduling.domain.models import (
    CoreScheduleBlock,
    ScheduleBlockStatus,
)
from app.modules.scheduling.engine.resource_conflict import ResourceConflictService
from app.modules.scheduling.engine.scheduling_engine import SchedulingEngine


def test_resource_conflict_detects_overlap(db, synced_scheduling, default_company):
    """ResourceConflictService detecta bloco sobreposto."""
    resource = synced_scheduling["resource"]
    starts = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=5)
    ends = starts + timedelta(hours=2)

    db.add(
        CoreScheduleBlock(
            company_id=default_company.id,
            resource_id=resource.id,
            location_id=synced_scheduling["location"].id,
            starts_at=starts,
            ends_at=ends,
            status=ScheduleBlockStatus.SCHEDULED,
        )
    )
    db.commit()

    svc = ResourceConflictService(db)
    assert svc.has_conflict(
        resource.id,
        default_company.id,
        starts + timedelta(minutes=30),
        starts + timedelta(hours=1),
    )


def test_scheduling_engine_availability_marks_conflict(
    db, synced_scheduling, default_company, tranca_exemplo, service_image_exemplo
):
    """SchedulingEngine marca slots indisponíveis quando há bloco core."""
    resource = synced_scheduling["resource"]
    catalog = synced_scheduling["catalog"]
    offering = synced_scheduling["offering"]
    target_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=6)

    block_start = target_day.replace(hour=10, minute=0)
    db.add(
        CoreScheduleBlock(
            company_id=default_company.id,
            resource_id=resource.id,
            location_id=synced_scheduling["location"].id,
            starts_at=block_start,
            ends_at=block_start + timedelta(hours=2),
            status=ScheduleBlockStatus.SCHEDULED,
        )
    )
    db.commit()

    engine = SchedulingEngine(db)
    slots = engine.check_availability(
        company_id=default_company.id,
        resource_id=resource.id,
        target_date=target_day,
        duration_minutes=offering.duration_minutes or 60,
        legacy_tranca_id=tranca_exemplo.id,
        legacy_service_image_id=service_image_exemplo.id,
        merge_legacy=True,
    )
    slot_10 = next(s for s in slots if s.starts_at.hour == 10 and s.starts_at.minute == 0)
    assert slot_10.available is False


def test_v1_scheduling_conflicts_endpoint(client, synced_scheduling):
    """POST /v1/scheduling/conflicts retorna has_conflict."""
    resource = synced_scheduling["resource"]
    starts = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=7)
    ends = starts + timedelta(hours=1)

    response = client.post(
        "/v1/scheduling/conflicts",
        json={
            "resource_id": resource.id,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "has_conflict" in body
    assert body["resource_id"] == resource.id
    assert body["capacity"] >= 1
