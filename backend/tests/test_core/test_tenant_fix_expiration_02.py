"""
FIX-EXPIRATION-02A/02B — ``expiration.reference`` e ``eligible_statuses`` por tenant.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.user import User
from app.models.user_company import CompanyRole
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.models import BookingPolicyConfig
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.company_service import CompanyService
from app.services.disponibilidade_service import DisponibilidadeService
from app.shared.events.outbox import CoreEventOutbox


@pytest.fixture
def enable_booking_core(monkeypatch):
    """
    Habilita ``booking.core.enabled`` para o path de ExpireBookingHandler.

    Args:
        monkeypatch: Fixture pytest.

    Yields:
        None.
    """

    def _flag(key: str) -> bool:
        return key == "booking.core.enabled"

    monkeypatch.setattr(
        "app.modules.booking.application.commands.expire_booking.feature_flags.is_enabled",
        _flag,
    )


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


def _create_admin(db, email: str, company: Company) -> User:
    """
    Cria admin OWNER do tenant.

    Args:
        db: Sessão.
        email: E-mail.
        company: Tenant.

    Returns:
        User.
    """
    user = User(
        email=email,
        nome="Exp02 Admin",
        hashed_password=get_password_hash("123456"),
        ativo=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    CompanyService(db).assign_user(user, company, CompanyRole.OWNER)
    return user


def _auth_headers(user: User, company: Company) -> dict:
    """
    Headers Bearer com tenant.

    Args:
        user: Usuário.
        company: Empresa.

    Returns:
        Headers HTTP.
    """
    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "company_id": company.id,
            "role": "owner",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _upsert_expiration(db, company_id: int, **expiration_fields) -> None:
    """
    Grava override de campos ``expiration.*`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        **expiration_fields: Campos de ``ExpirationPolicy`` a sobrescrever
            (ex.: ``reference``, ``eligible_statuses``, ``after_hours``).
    """
    payload = {"expiration": dict(expiration_fields)}
    now = datetime.utcnow()
    row = (
        db.query(BookingPolicyConfig)
        .filter(BookingPolicyConfig.company_id == company_id)
        .first()
    )
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


def _create_pending_booking(
    db,
    company: Company,
    cliente,
    synced_catalog,
    *,
    created_at: datetime,
    deposit_paid: bool = False,
    deleted_at: datetime | None = None,
    status: ReservationStatus = ReservationStatus.PENDING_PAYMENT,
    payment_status: StatusPagamento = StatusPagamento.PENDING_PAYMENT,
    scheduled_at: datetime | None = None,
) -> CoreBooking:
    """
    Persiste booking pendente com timestamps controlados.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Par catalog/offering.
        created_at: Timestamp de criação.
        deposit_paid: Sinal pago.
        deleted_at: Soft-delete.
        status: Status da reserva.
        payment_status: Status de pagamento.
        scheduled_at: Início do slot.

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=scheduled_at or (datetime.now() + timedelta(days=40)),
        status=status,
        payment_status=payment_status,
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=deposit_paid,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        deleted_at=deleted_at,
        created_at=created_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.created_at = created_at
    if scheduled_at is not None:
        row.scheduled_at = scheduled_at
    db.commit()
    db.refresh(row)
    return row


def _outbox_expired_count(db, booking_id: int) -> int:
    """
    Conta eventos ``booking.expired`` do booking.

    Args:
        db: Sessão.
        booking_id: ID do booking.

    Returns:
        Quantidade.
    """
    return (
        db.query(CoreEventOutbox)
        .filter(
            CoreEventOutbox.event_type == "booking.expired",
            CoreEventOutbox.aggregate_id == str(booking_id),
        )
        .count()
    )


def _patch_fixed_now(monkeypatch, fixed_now: datetime) -> None:
    """
    Congela ``datetime.now`` usado pelo serviço de disponibilidade.

    Args:
        monkeypatch: Fixture pytest.
        fixed_now: Instantâneo retornado por ``now`` (naive = UTC).
    """

    class _FixedDateTime(datetime):
        """
        Subclasse de ``datetime`` com ``now()`` fixo.
        """

        @classmethod
        def now(cls, tz=None):
            """
            Retorna o instante fixo do teste.

            Args:
                tz: Se informado, aplica tzinfo; senão retorna naive.

            Returns:
                Datetime fixo.
            """
            if tz is None:
                return fixed_now
            if fixed_now.tzinfo is None:
                return fixed_now.replace(tzinfo=tz)
            return fixed_now.astimezone(tz)

    monkeypatch.setattr(
        "app.services.disponibilidade_service.datetime",
        _FixedDateTime,
    )


# ---------------------------------------------------------------------------
# Reference (02A)
# ---------------------------------------------------------------------------


def test_01_default_created_at_preserva_comportamento(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Sem override, default ``reference=created_at`` expira após 2h."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=3),
    )
    count = DisponibilidadeService(db).expirar_reservas_pendentes()
    assert count >= 1
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_02_override_reference_created_at(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Override explícito ``reference=created_at`` mantém janela por criação."""
    _upsert_expiration(db, default_company.id, reference="created_at", after_hours=2)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=3),
        scheduled_at=datetime.now() + timedelta(days=5),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_03_04_scheduled_at_futuro_nao_expira_por_created_antigo(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``reference=scheduled_at``: created antigo + scheduled futuro → não expira."""
    _upsert_expiration(db, default_company.id, reference="scheduled_at", after_hours=2)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=10),
        scheduled_at=datetime.now() + timedelta(days=2),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_05_scheduled_at_passado_fora_janela_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``reference=scheduled_at`` com horário passado e fora da janela expira."""
    _upsert_expiration(db, default_company.id, reference="scheduled_at", after_hours=2)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=10),
        scheduled_at=datetime.now() - timedelta(hours=5),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_06_scheduled_at_none_nao_expira_nem_quebra_lote(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """``scheduled_at=None`` com reference=scheduled_at: skip; outro booking expira."""
    from app.modules.booking.domain.models import CoreBooking as CB

    _upsert_expiration(db, default_company.id, reference="scheduled_at", after_hours=2)
    booking_ok = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=5),
        scheduled_at=datetime.now() - timedelta(hours=5),
    )
    fake = SimpleNamespace(
        id=9_999_992,
        company_id=default_company.id,
        created_at=datetime.now() - timedelta(hours=10),
        scheduled_at=None,
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
        deleted_at=None,
    )

    real_query = db.query
    injected = {"done": False}

    def query_proxy(model):
        """
        Injeta booking com ``scheduled_at=None`` nos candidatos.

        Args:
            model: Modelo SQLAlchemy.

        Returns:
            Query possivelmente com ``.all`` monkeypatched.
        """
        q = real_query(model)
        if model is CB and not injected["done"]:
            original_all = q.all

            def all_with_fake():
                """
                Retorna candidatos reais + fake sem scheduled_at.

                Returns:
                    Lista de bookings.
                """
                injected["done"] = True
                return list(original_all()) + [fake]

            q.all = all_with_fake  # type: ignore[method-assign]
        return q

    monkeypatch.setattr(db, "query", query_proxy)
    count = DisponibilidadeService(db).expirar_reservas_pendentes()
    assert count >= 1
    db.refresh(booking_ok)
    assert booking_ok.status == ReservationStatus.EXPIRED


def test_07_limite_exato_nao_inclusivo(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """``reference_ts == now - after_hours`` não expira (comparação exclusiva)."""
    fixed_now = datetime(2026, 7, 29, 15, 0, 0)
    created_at = fixed_now - timedelta(hours=2)
    _patch_fixed_now(monkeypatch, fixed_now)
    _upsert_expiration(db, default_company.id, reference="created_at", after_hours=2)

    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created_at,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_08_tenants_referencias_diferentes_isolados(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Tenant A usa created_at; B usa scheduled_at — políticas não se cruzam."""
    company_b = _create_company(db, "exp02-ref-b")
    _upsert_expiration(db, default_company.id, reference="created_at", after_hours=2)
    _upsert_expiration(db, company_b.id, reference="scheduled_at", after_hours=2)

    created_old = datetime.now() - timedelta(hours=5)
    scheduled_future = datetime.now() + timedelta(days=3)
    scheduled_past = datetime.now() - timedelta(hours=5)

    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        scheduled_at=scheduled_future,
    )
    booking_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(minutes=5),
        scheduled_at=scheduled_past,
    )
    booking_b_keep = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created_old,
        scheduled_at=scheduled_future,
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_a)
    db.refresh(booking_b)
    db.refresh(booking_b_keep)
    assert booking_a.status == ReservationStatus.EXPIRED
    assert booking_b.status == ReservationStatus.EXPIRED
    assert booking_b_keep.status == ReservationStatus.PENDING_PAYMENT


# ---------------------------------------------------------------------------
# Eligible statuses (02B)
# ---------------------------------------------------------------------------


def test_09_pending_payment_elegivel_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Lista com ``pending_payment`` expira booking nesse status."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending_payment"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_10_status_nao_incluido_ignorado(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``pending_payment`` fora da lista elegível não expira."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending_approval"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_11_pending_approval_elegivel_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``pending_approval`` na lista e persistido → expira (lifecycle PENDING)."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending_approval"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_APPROVAL,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_12_waiting_time_confirmation_elegivel_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``waiting_time_confirmation`` na lista e persistido → expira."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["waiting_time_confirmation"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.WAITING_TIME_CONFIRMATION,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


def test_13_pending_ambiguo_nao_expande(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Alias ``pending`` sozinho não expande para pending_payment (fail-closed)."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_13b_pendente_explicito_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Alias ``pendente`` explícito só casa com status ORM ``PENDENTE``."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pendente"],
        after_hours=2,
    )
    booking_pendente = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDENTE,
    )
    booking_payment = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_pendente)
    db.refresh(booking_payment)
    assert booking_pendente.status == ReservationStatus.EXPIRED
    assert booking_payment.status == ReservationStatus.PENDING_PAYMENT


@pytest.mark.parametrize(
    "status",
    [
        ReservationStatus.APPROVED,
        ReservationStatus.COMPLETED,
        ReservationStatus.CANCELLED,
        ReservationStatus.NO_SHOW,
        ReservationStatus.EXPIRED,
    ],
)
def test_14_15_status_finais_nunca_expiram(
    db,
    default_company,
    cliente_exemplo,
    synced_catalog,
    enable_booking_core,
    status,
):
    """approved/completed/cancelled/no_show/expired nunca expiram via config."""
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending_payment", "pending_approval", "pendente"],
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        status=status,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == status
    assert booking.deleted_at is None


def test_16_falha_status_nao_interrompe_outro_tenant(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Booking incompatível em A não impede expiração elegível em B."""
    company_b = _create_company(db, "exp02-st-b")
    _upsert_expiration(
        db,
        default_company.id,
        eligible_statuses=["pending_approval"],
        after_hours=2,
    )
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        status=ReservationStatus.PENDING_PAYMENT,
    )
    booking_b = _create_pending_booking(
        db,
        company_b,
        cliente_exemplo,
        synced_catalog,
        created_at=created,
        status=ReservationStatus.PENDING_PAYMENT,
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


# ---------------------------------------------------------------------------
# Depósito e regressão
# ---------------------------------------------------------------------------


def test_17_18_deposito_false_expira_true_nao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``deposit_paid=False`` expira; ``True`` permanece pendente."""
    unpaid = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=False,
    )
    paid = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(unpaid)
    db.refresh(paid)
    assert unpaid.status == ReservationStatus.EXPIRED
    assert paid.status == ReservationStatus.PENDING_PAYMENT


def test_19_require_unpaid_deposit_false_nao_libera_pago(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """``require_unpaid_deposit=false`` não libera expiração de depósito pago."""
    _upsert_expiration(
        db,
        default_company.id,
        require_unpaid_deposit=False,
        after_hours=2,
    )
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deposit_paid=True,
        payment_status=StatusPagamento.PARTIALLY_PAID,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_20_21_22_payment_intact_deleted_outbox_unico(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Após expirar: payment intacto, deleted_at set, outbox único no retry."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        payment_status=StatusPagamento.PENDING_PAYMENT,
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.payment_status == StatusPagamento.PENDING_PAYMENT
    assert booking.deleted_at is not None
    events_first = _outbox_expired_count(db, booking.id)
    assert events_first == 1

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert _outbox_expired_count(db, booking.id) == events_first


def test_23_version_conflict_nao_quebra_lote(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Conflito de versão em um booking não impede outro do lote."""
    from app.core.exceptions import VersionConflictError
    from app.modules.booking.application.commands.expire_booking import (
        ExpireBookingHandler,
    )

    created = datetime.now() - timedelta(hours=5)
    booking_fail = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    company_b = _create_company(db, "exp02-ver-b")
    booking_ok = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    real_execute = ExpireBookingHandler.execute

    def _execute(self, command):
        """
        Simula VersionConflictError no primeiro booking.

        Args:
            self: Handler.
            command: Comando expire.

        Returns:
            Resultado real do handler.

        Raises:
            VersionConflictError: Para o booking alvo.
        """
        if command.booking_id == booking_fail.id:
            raise VersionConflictError()
        return real_execute(self, command)

    monkeypatch.setattr(ExpireBookingHandler, "execute", _execute)
    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_fail)
    db.refresh(booking_ok)
    assert booking_fail.status == ReservationStatus.PENDING_PAYMENT
    assert booking_ok.status == ReservationStatus.EXPIRED


def test_24_enabled_e_after_hours_exp01_ok(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Regressão FIX-EXPIRATION-01: enabled=false e after_hours=6."""
    company_b = _create_company(db, "exp02-reg-b")
    _upsert_expiration(db, default_company.id, enabled=False, after_hours=2)
    _upsert_expiration(db, company_b.id, after_hours=6)

    created_3h = datetime.now() - timedelta(hours=3)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created_3h
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created_3h
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.PENDING_PAYMENT

    booking_b.created_at = datetime.now() - timedelta(hours=7)
    db.commit()
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking_b)
    assert booking_b.status == ReservationStatus.EXPIRED


def test_25_api_booking_policy_persiste_reference_e_statuses(
    client, db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """PUT /admin/booking-policy persiste reference/eligible e afeta o lote."""
    admin = _create_admin(db, "exp02-api@test.local", default_company)
    resp = client.put(
        "/admin/booking-policy",
        json={
            "expiration": {
                "reference": "scheduled_at",
                "eligible_statuses": ["pending_payment"],
                "after_hours": 2,
            }
        },
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    expiration = body.get("policy", body).get("expiration", {})
    assert expiration.get("reference") == "scheduled_at"
    assert "pending_payment" in expiration.get("eligible_statuses", [])

    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=10),
        scheduled_at=datetime.now() + timedelta(days=2),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_helper_reference_desconhecida_fail_closed():
    """Helper: reference desconhecida retorna None (fail-closed)."""
    booking = SimpleNamespace(id=1, created_at=datetime.now(), scheduled_at=datetime.now())
    assert (
        DisponibilidadeService._expiration_reference_timestamp(booking, "unknown")
        is None
    )


def test_helper_eligible_ignora_alias_pending():
    """Helper: ``pending`` não autoriza ``pending_payment``."""
    assert not DisponibilidadeService._expiration_status_is_eligible(
        ReservationStatus.PENDING_PAYMENT,
        ("pending",),
    )
    assert DisponibilidadeService._expiration_status_is_eligible(
        ReservationStatus.PENDING_PAYMENT,
        ("pending_payment",),
    )
