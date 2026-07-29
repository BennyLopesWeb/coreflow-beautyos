"""
FIX-CANCEL-POLICY-01 — janela de cancelamento configurável por tenant.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import CancelPolicyViolationError
from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.exceptions import InvalidBookingStateTransitionError
from app.modules.booking.domain.policy.cancel_window import (
    can_cancel_approved,
    ensure_utc,
    may_cancel_for_lifecycle,
)
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.services.booking_domain_service import BookingDomainService
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    MoneySnapshot,
    TimeSlot,
)
from app.modules.booking.infrastructure.adapters.cancel_policy_adapter import (
    LegacyCancelPolicyAdapter,
)
from app.models.company import Company, CompanyPlan, CompanySegment


def _booking(
    *,
    status: BookingLifecycleStatus = BookingLifecycleStatus.APPROVED,
    starts_at: datetime,
    company_id: int = 1,
) -> Booking:
    """
    Monta aggregate mínimo para testes de janela.

    Args:
        status: Lifecycle.
        starts_at: Início do slot.
        company_id: Tenant.

    Returns:
        Booking de teste.
    """
    return Booking(
        company_id=company_id,
        customer_id=2,
        catalog_id=3,
        offering_id=4,
        time_slot=TimeSlot(starts_at=starts_at, ends_at=starts_at + timedelta(hours=1)),
        pricing=MoneySnapshot(
            price_total=Decimal("100"),
            deposit_pct=Decimal("0.3"),
            deposit_amount=Decimal("30"),
            remaining_amount=Decimal("70"),
        ),
        status=status,
        id=10,
        version=1,
    )


class _FixedClock:
    """
    Clock injetável com instante fixo.

    Args:
        instant: Datetime retornado por ``now_utc``.
    """

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now_utc(self) -> datetime:
        """
        Retorna o instante configurado.

        Returns:
            Datetime do clock.
        """
        return self._instant


def _create_company(db, slug: str) -> Company:
    """
    Persiste empresa auxiliar.

    Args:
        db: Sessão.
        slug: Slug único.

    Returns:
        Company.
    """
    co = Company(
        nome=slug,
        slug=slug,
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(co)
    db.commit()
    db.refresh(co)
    return co


def _upsert_cancel_hours(db, company_id: int, hours: int) -> None:
    """
    Grava override de ``approved_min_hours_before`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        hours: Valor N.
    """
    now = datetime.utcnow()
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == company_id)
        .first()
    )
    payload = {"cancellation": {"approved_min_hours_before": hours}}
    if row is None:
        db.add(
            BookingPolicyConfig(
                company_id=company_id,
                policy_json=payload,
                version=1,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        row.policy_json = payload
        row.is_active = True
        row.updated_at = now
    db.commit()


# ---------------------------------------------------------------------------
# Função pura / boundary
# ---------------------------------------------------------------------------


def test_01_default_24h_boundary_inclusive():
    """Sem override conceitual: N=24 no limite exato permite; +1s bloqueia."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    assert can_cancel_approved(
        datetime(2026, 7, 9, 15, 0, tzinfo=timezone.utc), start, 24
    )
    assert not can_cancel_approved(
        datetime(2026, 7, 9, 15, 1, tzinfo=timezone.utc), start, 24
    )


def test_06_08_antes_e_no_limite():
    """Antes do limite e exatamente no limite → permitido."""
    start = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert can_cancel_approved(
        datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc), start, 48
    )
    assert can_cancel_approved(
        datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc), start, 48
    )


def test_09_10_n_zero():
    """N=0 permite até o início; após o início bloqueia."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    assert can_cancel_approved(start, start, 0)
    assert not can_cancel_approved(
        start + timedelta(seconds=1), start, 0
    )


def test_11_12_n_one():
    """N=1: exatamente 1h antes permite; depois bloqueia."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    assert can_cancel_approved(
        datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc), start, 1
    )
    assert not can_cancel_approved(
        datetime(2026, 7, 10, 14, 0, 1, tzinfo=timezone.utc), start, 1
    )


def test_13_14_pending_vs_approved():
    """Pending ignora janela; approved aplica."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    late = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    assert may_cancel_for_lifecycle(
        BookingLifecycleStatus.PENDING, late, start, 24
    )
    assert not may_cancel_for_lifecycle(
        BookingLifecycleStatus.APPROVED, late, start, 24
    )


def test_15_17_terminais_retornam_false_na_janela():
    """Estados terminais: may_cancel_for_lifecycle False (FSM bloqueia depois)."""
    start = datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
    now = datetime(2026, 7, 1, 15, 0, tzinfo=timezone.utc)
    for st in (
        BookingLifecycleStatus.COMPLETED,
        BookingLifecycleStatus.EXPIRED,
        BookingLifecycleStatus.NO_SHOW,
        BookingLifecycleStatus.RESCHEDULED,
        BookingLifecycleStatus.CANCELLED,
        BookingLifecycleStatus.REJECTED,
    ):
        assert may_cancel_for_lifecycle(st, now, start, 24) is False


def test_20_22_23_clock_e_timezone():
    """Clock injetado; naive = UTC; aware normalizado."""
    start_naive = datetime(2026, 7, 10, 15, 0)
    start_aware = datetime(2026, 7, 10, 12, 0, tzinfo=timezone(timedelta(hours=-3)))
    adapter = LegacyCancelPolicyAdapter(24)
    clock_ok = _FixedClock(datetime(2026, 7, 9, 15, 0, tzinfo=timezone.utc))
    clock_late = _FixedClock(datetime(2026, 7, 9, 15, 1, tzinfo=timezone.utc))

    b_naive = _booking(starts_at=start_naive)
    assert adapter.may_cancel(b_naive, clock_ok) is True
    assert adapter.may_cancel(b_naive, clock_late) is False

    # 12:00 -03 == 15:00 UTC — mesma deadline
    b_aware = _booking(starts_at=start_aware)
    assert adapter.may_cancel(b_aware, clock_ok) is True
    assert ensure_utc(start_aware) == datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)


def test_24_starts_at_vigente_remarcado():
    """Booking remarcado usa o starts_at atual do aggregate."""
    new_start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    booking = _booking(starts_at=new_start)
    adapter = LegacyCancelPolicyAdapter(24)
    assert adapter.may_cancel(
        booking, _FixedClock(datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc))
    )
    assert not adapter.may_cancel(
        booking, _FixedClock(datetime(2026, 8, 31, 10, 1, tzinfo=timezone.utc))
    )


# ---------------------------------------------------------------------------
# Adapter + domain
# ---------------------------------------------------------------------------


def test_02_03_override_por_tenant_e_isolamento(db):
    """Tenant A com N=48; B com default 24 — adapters independentes."""
    co_a = _create_company(db, "cancel01-a")
    co_b = _create_company(db, "cancel01-b")
    _upsert_cancel_hours(db, co_a.id, 48)

    from app.modules.booking.domain.policy.resolver import BookingPolicyResolver

    pol_a = BookingPolicyResolver(db).resolve(co_a.id)
    pol_b = BookingPolicyResolver(db).resolve(co_b.id)
    assert pol_a.cancellation.approved_min_hours_before == 48
    assert pol_b.cancellation.approved_min_hours_before == 24

    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    # 36h antes: bloqueado para A (exige 48h); permitido para B (exige 24h)
    now = datetime(2026, 7, 9, 3, 0, tzinfo=timezone.utc)
    assert not LegacyCancelPolicyAdapter(48).may_cancel(
        _booking(starts_at=start, company_id=co_a.id), _FixedClock(now)
    )
    assert LegacyCancelPolicyAdapter(24).may_cancel(
        _booking(starts_at=start, company_id=co_b.id), _FixedClock(now)
    )


def test_04_05_company_id_ausente_fail_closed():
    """Adapter rejeita N inválido; função pura falha fechada."""
    with pytest.raises(ValueError):
        LegacyCancelPolicyAdapter(-1)
    with pytest.raises(ValueError):
        can_cancel_approved(
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) + timedelta(days=1),
            -1,
        )


def test_27_domain_cancela_ou_viola():
    """Domain: janela OK cancela; violação → CancelPolicyViolationError."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    service = BookingDomainService()
    policy = LegacyCancelPolicyAdapter(24)

    ok = _booking(starts_at=start)
    cancelled = service.cancel(
        ok, policy, _FixedClock(datetime(2026, 7, 9, 15, 0, tzinfo=timezone.utc))
    )
    assert cancelled.status == BookingLifecycleStatus.CANCELLED

    late = _booking(starts_at=start)
    with pytest.raises(CancelPolicyViolationError):
        service.cancel(
            late,
            policy,
            _FixedClock(datetime(2026, 7, 9, 15, 1, tzinfo=timezone.utc)),
        )
    assert late.status == BookingLifecycleStatus.APPROVED


def test_15_19_fsm_terminais_bloqueados():
    """Domain bloqueia completed/expired/no_show/cancelled (comportamento atual)."""
    start = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    service = BookingDomainService()
    policy = LegacyCancelPolicyAdapter(24)
    clock = _FixedClock(datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc))

    for st in (
        BookingLifecycleStatus.COMPLETED,
        BookingLifecycleStatus.EXPIRED,
        BookingLifecycleStatus.NO_SHOW,
        BookingLifecycleStatus.RESCHEDULED,
        BookingLifecycleStatus.CANCELLED,
    ):
        booking = _booking(status=st, starts_at=start)
        with pytest.raises(InvalidBookingStateTransitionError):
            service.cancel(booking, policy, clock)


def test_13_pending_cancela_sem_janela():
    """Pending cancela mesmo dentro da janela que bloquearia approved."""
    start = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
    booking = _booking(status=BookingLifecycleStatus.PENDING, starts_at=start)
    result = BookingDomainService().cancel(
        booking,
        LegacyCancelPolicyAdapter(24),
        _FixedClock(datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)),
    )
    assert result.status == BookingLifecycleStatus.CANCELLED


def test_hardcode_24_removido_do_adapter_source():
    """Garante que o adapter não embute ``timedelta(hours=24)`` fixo."""
    import inspect
    from app.modules.booking.infrastructure.adapters import cancel_policy_adapter as mod

    src = inspect.getsource(mod)
    assert "timedelta(hours=24)" not in src
    assert "approved_min_hours_before" in src


def test_handler_resolve_n_do_tenant(
    client,
    db,
    synced_catalog,
    cliente_exemplo,
    default_company,
    booking_headers,
    monkeypatch,
):
    """
    CancelBookingHandler injeta N do resolver do ``booking.company_id``.
    """
    from app.modules.booking.application.commands.cancel_booking import (
        CancelBookingCommand,
        CancelBookingHandler,
    )
    from app.modules.booking.domain.models import CoreBooking
    from app.models.agendamento import ReservationStatus, StatusPagamento

    monkeypatch.setattr(
        "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
        lambda key: key == "booking.core.enabled",
    )
    _upsert_cancel_hours(db, default_company.id, 72)

    catalog, offering = synced_catalog
    start = datetime.now(timezone.utc) + timedelta(days=10)
    row = CoreBooking(
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=start,
        status=ReservationStatus.APPROVED,
        payment_status=StatusPagamento.PARTIALLY_PAID,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=True,
        sync_status="synced",
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    captured: dict = {}
    real_init = LegacyCancelPolicyAdapter.__init__

    def _spy(self, approved_min_hours_before: int = 24) -> None:
        captured["n"] = approved_min_hours_before
        real_init(self, approved_min_hours_before)

    monkeypatch.setattr(LegacyCancelPolicyAdapter, "__init__", _spy)
    # Janela 72h; clock 80h antes → permite
    monkeypatch.setattr(
        "app.modules.booking.application.commands.cancel_booking.SystemClockAdapter.now_utc",
        lambda self: start - timedelta(hours=80),
    )

    result = CancelBookingHandler(db).execute(
        CancelBookingCommand(
            booking_id=row.id,
            company_id=default_company.id,
            reason="policy-01",
        )
    )
    assert captured.get("n") == 72
    assert result.status == ReservationStatus.CANCELLED
    assert result.payment_status == StatusPagamento.CANCELLED
    assert result.deleted_at is not None


def test_28_http_409_cancel_policy_violation(
    client, admin_headers, synced_catalog, cliente_exemplo, db, booking_headers, monkeypatch
):
    """Violação da janela no path HTTP continua 409."""
    from app.services.disponibilidade_service import DisponibilidadeService
    from app.services.payment_reservation_service import PaymentReservationService

    monkeypatch.setattr(
        "app.modules.booking.application.commands.cancel_booking.feature_flags.is_enabled",
        lambda key: key in ("booking.core.enabled",),
    )
    monkeypatch.setattr(
        "app.modules.booking.application.commands.create_booking.feature_flags.is_enabled",
        lambda key: key in ("booking.core.enabled",),
    )
    monkeypatch.setattr(
        "app.modules.booking.application.commands.approve_booking.feature_flags.is_enabled",
        lambda key: key in ("booking.core.enabled",),
    )

    catalog, offering = synced_catalog
    horarios = DisponibilidadeService(db).calcular_horarios_disponiveis(
        datetime.now() + timedelta(days=5),
        catalog.legacy_tranca_id,
        offering.legacy_service_image_id,
    )
    slot = next(h for h in horarios if h.disponivel).horario
    create = client.post(
        "/v1/bookings",
        json={
            "customer_id": cliente_exemplo.id,
            "catalog_id": catalog.id,
            "offering_id": offering.id,
            "scheduled_at": slot.isoformat(),
        },
        headers=booking_headers(),
    )
    assert create.status_code == 201, create.text
    booking_id = create.json()["id"]
    PaymentReservationService(db).confirmar_deposito_por_booking(
        booking_id, company_id=cliente_exemplo.company_id
    )
    assert client.post(
        f"/v1/bookings/{booking_id}/approve", headers=admin_headers
    ).status_code == 200

    monkeypatch.setattr(
        LegacyCancelPolicyAdapter,
        "may_cancel",
        lambda self, booking, clock: False,
    )
    cancel = client.post(
        f"/v1/bookings/{booking_id}/cancel",
        headers=admin_headers,
        json={},
    )
    assert cancel.status_code == 409
    assert "cancel_policy_violation" in cancel.text
