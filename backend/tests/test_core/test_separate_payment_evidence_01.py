"""
SEPARATE-PAYMENT-EVIDENCE-01 — comprovante é evidência, não liquidação.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.company import Company, CompanyPlan, CompanySegment
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.policy.paid_amount import get_effective_paid_snapshot
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.modules.payments.models import CorePayment, CorePaymentStatus
from app.services.comprovante_service import ComprovanteService
from app.services.disponibilidade_service import DisponibilidadeService


class _FakeUpload:
    """
    UploadFile mínimo para testes.

    Attributes:
        content_type: MIME type.
        _data: Bytes.
    """

    def __init__(self, data: bytes = b"\xff\xd8\xff evidence", content_type: str = "image/jpeg"):
        """
        Args:
            data: Conteúdo.
            content_type: MIME.
        """
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        """
        Retorna bytes do arquivo fake.

        Returns:
            Payload.
        """
        return self._data


@pytest.fixture
def enable_booking_core(monkeypatch):
    """
    Habilita ExpireBookingHandler.

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


def _booking(db, company, cliente, synced_catalog, **kwargs) -> CoreBooking:
    """
    Cria booking pendente com cotação explícita.

    Args:
        db: Sessão.
        company: Tenant.
        cliente: Cliente.
        synced_catalog: Catalog/offering.
        **kwargs: Overrides (``created_at``, ``deposit_amount``, etc.).

    Returns:
        CoreBooking.
    """
    catalog, offering = synced_catalog
    price_total = kwargs.pop("price_total", Decimal("300.00"))
    deposit_amount = kwargs.pop("deposit_amount", Decimal("90.00"))
    created_at = kwargs.pop("created_at", datetime.utcnow())
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=kwargs.pop("scheduled_at", datetime.now() + timedelta(days=20)),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=StatusPagamento.PENDING_PAYMENT,
        price_total=price_total,
        deposit_pct=Decimal("0.30"),
        deposit_amount=deposit_amount,
        remaining_amount=(price_total - deposit_amount).quantize(Decimal("0.01")),
        deposit_paid=kwargs.pop("deposit_paid", False),
        sync_status=SyncStatus.SYNCED.value,
        version=1,
        created_at=created_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row.created_at = created_at
    db.commit()
    db.refresh(row)
    return row


@pytest.mark.asyncio
async def test_upload_nao_usa_cotacao_nem_marca_pago(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Upload grava evidência PENDING com valor 0; deposit_paid permanece False."""
    booking = _booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        deposit_amount=Decimal("90.00"),
    )
    pag = await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(),
        company_id=default_company.id,
        base_url="http://testserver",
    )
    db.refresh(booking)
    assert pag.status == PaymentStatus.PENDING
    assert pag.valor == Decimal("0.00")
    assert pag.valor != booking.deposit_amount
    assert pag.paid_at is None
    assert booking.deposit_paid is False
    assert booking.status == ReservationStatus.PENDING_PAYMENT

    core = (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag.id)
        .one()
    )
    assert core.status == CorePaymentStatus.PENDING
    assert core.amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_reenvio_idempotente_nao_duplica(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Reenvio atualiza URL e limpa cotação residual; um Payment e um CorePayment."""
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    # Linha legada ambígua (cotação em valor).
    legacy = Payment(
        booking_id=booking.id,
        tipo=PaymentType.DEPOSIT,
        valor=booking.deposit_amount,
        status=PaymentStatus.PENDING,
    )
    db.add(legacy)
    db.commit()

    pag1 = await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(b"\xff\xd8\xff a"),
        company_id=default_company.id,
        base_url="http://testserver",
    )
    url1 = pag1.comprovante_url
    pag2 = await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(b"\xff\xd8\xff b"),
        company_id=default_company.id,
        base_url="http://testserver",
    )
    assert pag2.id == pag1.id
    assert pag2.comprovante_url != url1
    assert pag2.valor == Decimal("0.00")
    assert (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.tipo == PaymentType.DEPOSIT,
            Payment.deleted_at.is_(None),
        )
        .count()
        == 1
    )
    assert (
        db.query(CorePayment)
        .filter(CorePayment.legacy_payment_id == pag2.id)
        .count()
        == 1
    )


@pytest.mark.asyncio
async def test_comprovante_nao_conta_no_snapshot_nem_impede_expiracao(
    db, default_company, cliente_exemplo, synced_catalog, enable_booking_core
):
    """PENDING de evidência não satisfaz mínimo e não bloqueia expiração."""
    booking = _booking(
        db,
        default_company,
        cliente_exemplo,
        synced_catalog,
        created_at=datetime.now() - timedelta(hours=5),
        price_total=Decimal("300.00"),
        deposit_amount=Decimal("90.00"),
    )

    await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(),
        company_id=default_company.id,
        base_url="http://testserver",
    )

    snap = get_effective_paid_snapshot(
        db, booking_id=booking.id, company_id=default_company.id
    )
    assert snap.paid_cents == 0
    assert snap.has_paid_rows is False

    DisponibilidadeService(db).expirar_reservas_pendentes()
    db.refresh(booking)
    assert booking.status == ReservationStatus.EXPIRED


@pytest.mark.asyncio
async def test_tenant_isola_upload(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Upload com company_id de outro tenant não encontra o booking."""
    from app.core.exceptions import NotFoundError

    company_b = Company(
        nome="ev-b",
        slug="ev-b",
        segmento=CompanySegment.TRANCISTA,
        plano=CompanyPlan.FREE,
        timezone="America/Sao_Paulo",
        ativo=True,
    )
    db.add(company_b)
    db.commit()
    db.refresh(company_b)

    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    with pytest.raises(NotFoundError):
        await ComprovanteService(db).salvar_comprovante_por_booking(
            booking_id=booking.id,
            arquivo=_FakeUpload(),
            company_id=company_b.id,
            base_url="http://testserver",
        )


def test_upsert_payment_por_booking_ausente():
    """Regressão PR #44: helper morto continua removido."""
    import app.services.payment_reservation_service as mod

    assert not hasattr(
        mod.PaymentReservationService, "_upsert_payment_por_booking"
    )
