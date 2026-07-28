"""R4-F15 — Upload de comprovante core-only (booking_id).

Cobertura:
- APP_VERSION == 2.18.0-r4-f15.
- ``ComprovanteService.salvar_comprovante_por_booking`` cria Payment DEPOSIT.
- ``POST /v1/bookings/{id}/comprovante`` (multipart) persiste URL.
- Rejeita quando deposit_paid; 410 no path legado permanece.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.legacy_gone import match_legacy_gone
from app.models.agendamento import ReservationStatus, StatusPagamento
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.booking.domain.value_objects.booking_types import SyncStatus
from app.services.comprovante_service import COMPROVANTES_DIR, ComprovanteService


def _booking(db, company, cliente, synced_catalog, *, deposit_paid: bool = False):
    """
    Cria CoreBooking de teste para R4-F15.

    Args:
        db: Sessão SQLAlchemy.
        company: Empresa seed.
        cliente: Cliente seed.
        synced_catalog: Par (catalog, offering).
        deposit_paid: Se o sinal já foi confirmado.

    Returns:
        CoreBooking persistido.
    """
    catalog, offering = synced_catalog
    row = CoreBooking(
        company_id=company.id,
        customer_id=cliente.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        scheduled_at=datetime.now() + timedelta(days=96),
        status=ReservationStatus.PENDING_PAYMENT,
        payment_status=(
            StatusPagamento.PARTIALLY_PAID
            if deposit_paid
            else StatusPagamento.PENDING_PAYMENT
        ),
        price_total=Decimal("100.00"),
        deposit_pct=Decimal("0.30"),
        deposit_amount=Decimal("30.00"),
        remaining_amount=Decimal("70.00"),
        deposit_paid=deposit_paid,
        legacy_agendamento_id=None,
        sync_status=SyncStatus.SYNCED.value,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


class _FakeUpload:
    """
    UploadFile mínimo para testes unitários do service.

    Attributes:
        content_type: MIME type.
        _data: Bytes do arquivo.
    """

    def __init__(self, data: bytes, content_type: str = "image/jpeg"):
        """
        Args:
            data: Conteúdo binário.
            content_type: MIME type simulado.
        """
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        """
        Retorna o conteúdo completo do arquivo fake.

        Returns:
            Bytes do payload.
        """
        return self._data


def test_app_version_r4_f15():
    """APP_VERSION marca R4-F15 (upload comprovante core)."""
    assert settings.APP_VERSION == "2.18.0-r4-f15"


def test_legado_comprovante_continua_410():
    """Path legado /pagamentos/comprovante permanece no mapa 410."""
    assert match_legacy_gone("/pagamentos/comprovante/1").successor == "/v1/payments"


@pytest.mark.asyncio
async def test_salvar_comprovante_cria_payment_deposit(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    Service grava arquivo e cria Payment DEPOSIT com comprovante_url.
    """
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    pag = await ComprovanteService(db).salvar_comprovante_por_booking(
        booking_id=booking.id,
        arquivo=_FakeUpload(b"\xff\xd8\xff fake-jpeg"),
        company_id=default_company.id,
        base_url="http://testserver",
    )
    assert pag.booking_id == booking.id
    assert pag.tipo == PaymentType.DEPOSIT
    assert pag.status == PaymentStatus.PENDING
    assert pag.comprovante_url is not None
    assert "/static/comprovantes/booking_" in pag.comprovante_url
    assert str(booking.id) in pag.comprovante_url

    nome = Path(pag.comprovante_url).name
    assert (COMPROVANTES_DIR / nome).exists()


@pytest.mark.asyncio
async def test_salvar_comprovante_rejeita_sinal_ja_pago(
    db, default_company, cliente_exemplo, synced_catalog
):
    """Com deposit_paid=True o upload falha com ValidationError."""
    booking = _booking(
        db, default_company, cliente_exemplo, synced_catalog, deposit_paid=True
    )
    with pytest.raises(ValidationError):
        await ComprovanteService(db).salvar_comprovante_por_booking(
            booking_id=booking.id,
            arquivo=_FakeUpload(b"abc"),
            company_id=default_company.id,
        )


def test_http_post_comprovante_booking(
    client, db, default_company, cliente_exemplo, synced_catalog
):
    """POST multipart /v1/bookings/{id}/comprovante → 201 + Payment."""
    booking = _booking(db, default_company, cliente_exemplo, synced_catalog)
    resp = client.post(
        f"/v1/bookings/{booking.id}/comprovante",
        files={"arquivo": ("comp.jpg", BytesIO(b"\xff\xd8\xffx"), "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["booking_id"] == booking.id
    assert "comprovante_url" in body
    assert "Comprovante recebido" in body["mensagem"]

    pag = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.tipo == PaymentType.DEPOSIT,
        )
        .first()
    )
    assert pag is not None
    assert pag.comprovante_url == body["comprovante_url"]


def test_http_comprovante_booking_inexistente_404(client):
    """Booking inexistente → 404."""
    resp = client.post(
        "/v1/bookings/999999/comprovante",
        files={"arquivo": ("comp.jpg", BytesIO(b"x"), "image/jpeg")},
    )
    assert resp.status_code == 404


def test_http_legado_comprovante_ainda_410(client):
    """POST /pagamentos/comprovante/{id} continua 410 Gone."""
    resp = client.post("/pagamentos/comprovante/1")
    assert resp.status_code == 410
