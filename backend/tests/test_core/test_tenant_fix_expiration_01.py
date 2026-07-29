"""
FIX-EXPIRATION-01 — ``expiration.enabled`` e ``after_hours`` por tenant na expiração lazy.
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
        nome="Exp01 Admin",
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


def _upsert_expiration(
    db,
    company_id: int,
    *,
    after_hours: int | None = None,
    enabled: bool | None = None,
) -> None:
    """
    Grava override de ``expiration.*`` para o tenant.

    Args:
        db: Sessão.
        company_id: Tenant.
        after_hours: Override de horas (opcional).
        enabled: Override de enabled (opcional).
    """
    payload: dict = {"expiration": {}}
    if after_hours is not None:
        payload["expiration"]["after_hours"] = after_hours
    if enabled is not None:
        payload["expiration"]["enabled"] = enabled
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
    Persiste booking pendente com ``created_at`` controlado.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Par catalog/offering.
        created_at: Timestamp de criação (janela).
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
    # Garante created_at mesmo se o ORM sobrescrever no insert.
    row.created_at = created_at
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


def test_01_default_expira_apos_2h(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Sem override, booking com created_at há 3h expira (default 2h)."""
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


def test_02_03_tenant_a_6h_b_default_mesmo_lote(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """A com after_hours=6 não expira em 3h; B default expira no mesmo lote."""
    company_b = _create_company(db, "exp01-co-b")
    _upsert_expiration(db, default_company.id, after_hours=6)

    created = datetime.now() - timedelta(hours=3)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_04_05_enabled_false_isola_tenant(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """enabled=false em A: A não expira; B continua expirando."""
    company_b = _create_company(db, "exp01-en-b")
    _upsert_expiration(db, default_company.id, enabled=False)

    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_06_limite_exato_nao_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """created_at == now - after_hours não expira (comparação exclusiva)."""
    fixed_now = datetime(2026, 7, 29, 15, 0, 0)
    created_at = fixed_now - timedelta(hours=2)

    class _FixedDateTime(datetime):
        """
        datetime com ``now()`` fixo para o teste de limite exclusivo.
        """

        @classmethod
        def now(cls, tz=None):
            """
            Retorna o instante fixo do teste.

            Args:
                tz: Ignorado (compatível com assinatura de ``datetime.now``).

            Returns:
                Datetime fixo.
            """
            return fixed_now

    monkeypatch.setattr(
        "app.services.disponibilidade_service.datetime",
        _FixedDateTime,
    )
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


def test_07_deposito_pago_nao_expira(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Depósito pago continua fora dos candidatos."""
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


def test_08_soft_deleted_ignorado(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Booking soft-deleted não é candidato."""
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        deleted_at=datetime.utcnow(),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT


def test_09_ja_expirado_idempotente(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Booking já expirado não gera novo evento nem altera estado."""
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
    deleted_first = booking.deleted_at
    events_first = _outbox_expired_count(db, booking.id)

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.deleted_at == deleted_first
    assert _outbox_expired_count(db, booking.id) == events_first


def test_10_sem_company_id_nao_quebra_lote(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Booking sem company_id é ignorado; outro do lote ainda expira."""
    from app.modules.booking.domain.models import CoreBooking as CB

    booking_ok = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
    )
    fake = SimpleNamespace(
        id=9_999_991,
        company_id=None,
        created_at=datetime.now() - timedelta(hours=5),
        status=ReservationStatus.PENDING_PAYMENT,
        deposit_paid=False,
        deleted_at=None,
    )

    real_query = db.query
    injected = {"done": False}

    def query_proxy(model):
        """
        Injeta booking sem ``company_id`` no ``.all()`` da query de candidatos.

        Args:
            model: Modelo SQLAlchemy.

        Returns:
            Query (possivelmente com ``.all`` monkeypatched).
        """
        q = real_query(model)
        if model is CB and not injected["done"]:
            original_all = q.all

            def all_with_fake():
                """
                Retorna candidatos reais + fake sem tenant.

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


def test_11_erro_resolve_nao_impede_outro_tenant(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core, monkeypatch
):
    """Falha ao resolver política de A não impede expiração de B."""
    company_b = _create_company(db, "exp01-fail-b")
    created = datetime.now() - timedelta(hours=5)
    booking_a = _create_pending_booking(
        db, default_company, cliente_exemplo, synced_catalog, created_at=created
    )
    booking_b = _create_pending_booking(
        db, company_b, cliente_exemplo, synced_catalog, created_at=created
    )

    from app.modules.booking.domain.policy.resolver import BookingPolicyResolver

    real_resolve = BookingPolicyResolver.resolve

    def _resolve(self, company_id: int):
        if company_id == default_company.id:
            raise RuntimeError("boom resolve A")
        return real_resolve(self, company_id)

    monkeypatch.setattr(BookingPolicyResolver, "resolve", _resolve)

    DisponibilidadeService(db).expirar_reservas_pendentes()

    db.refresh(booking_a)
    db.refresh(booking_b)
    assert booking_a.status == ReservationStatus.PENDING_PAYMENT
    assert booking_b.status == ReservationStatus.EXPIRED


def test_12_13_payment_intact_deleted_at_set(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Após expirar: payment_status intacto; deleted_at definido."""
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


def test_14_disponibilidade_libera_slot(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """Após expiração, booking soft-deleted não ocupa vaga."""
    from app.models.agendamento import STATUS_OCUPAM_VAGA

    slot = datetime.now().replace(second=0, microsecond=0) + timedelta(days=41)
    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        scheduled_at=slot,
    )
    assert booking.status in STATUS_OCUPAM_VAGA

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED
    assert booking.deleted_at is not None

    ocupados = DisponibilidadeService(db)._slots_ocupados(
        slot - timedelta(hours=1),
        slot + timedelta(hours=4),
    )
    assert slot not in ocupados


def test_15_put_booking_policy_reflete_no_lote(
    client, db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """PUT /admin/booking-policy com after_hours=6 impede expiração em 3h."""
    admin = _create_admin(db, "exp01-api@test.local", default_company)
    resp = client.put(
        "/admin/booking-policy",
        json={"expiration": {"after_hours": 6}},
        headers=_auth_headers(admin, default_company),
    )
    assert resp.status_code == 200, resp.text

    booking = _create_pending_booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=3),
    )
    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.PENDING_PAYMENT
