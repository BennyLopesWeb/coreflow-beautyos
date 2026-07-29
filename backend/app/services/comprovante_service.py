"""
Service para upload e gestão de comprovantes de depósito (R4-F15 core-only).
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.modules.booking.domain.models import CoreBooking
from app.modules.payments.legacy_sync import PaymentLegacySyncService

logger = get_logger("comprovante_service")

COMPROVANTES_DIR = Path(__file__).resolve().parents[1] / "static" / "comprovantes"
TIPOS_PERMITIDOS = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
}
EXTENSOES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
TAMANHO_MAX_BYTES = 5 * 1024 * 1024


class ComprovanteService:
    """
    Gerencia envio e armazenamento de comprovantes de depósito do sinal.

    R4-F15: vínculo autoritativo é ``core_bookings`` + ponte ``payments``
    (``booking_id``); o path legado ``agendamento_id`` foi removido.
    """

    def __init__(self, db: Session):
        """
        Inicializa o service com sessão do banco.

        Args:
            db: Sessão SQLAlchemy ativa.
        """
        self.db = db
        COMPROVANTES_DIR.mkdir(parents=True, exist_ok=True)

    async def salvar_comprovante_por_booking(
        self,
        booking_id: int,
        arquivo: UploadFile,
        company_id: Optional[int] = None,
        base_url: str = "http://localhost:8000",
    ) -> Payment:
        """
        Salva comprovante de depósito vinculado a um ``CoreBooking`` (R4-F15).

        Cria ou atualiza a linha ``payments`` (DEPOSIT/SINAL) com
        ``comprovante_url``. Não confirma o sinal — isso continua sendo
        ato do admin via ``confirmar_deposito_por_booking``.

        Args:
            booking_id: ID ``core_bookings.id``.
            arquivo: Arquivo enviado (imagem ou PDF).
            company_id: Tenant opcional para validação de isolamento.
            base_url: URL base da API para montar link público.

        Returns:
            ``Payment`` DEPOSIT atualizado com ``comprovante_url``.

        Raises:
            NotFoundError: Booking não encontrado (ou fora do tenant).
            ValidationError: Sinal já pago, tipo/tamanho inválidos.
        """
        q = self.db.query(CoreBooking).filter(CoreBooking.id == booking_id)
        if company_id is not None:
            q = q.filter(CoreBooking.company_id == company_id)
        booking = q.first()
        if not booking:
            raise NotFoundError("Booking", str(booking_id))

        if booking.deposit_paid:
            raise ValidationError("Sinal já foi confirmado para este booking")

        content_type = (arquivo.content_type or "").lower()
        if content_type not in TIPOS_PERMITIDOS:
            raise ValidationError(
                "Formato não permitido. Envie JPG, PNG, WEBP ou PDF."
            )

        conteudo = await arquivo.read()
        if len(conteudo) > TAMANHO_MAX_BYTES:
            raise ValidationError("Arquivo muito grande. Máximo: 5 MB.")
        if len(conteudo) == 0:
            raise ValidationError("Arquivo vazio.")

        ext = EXTENSOES.get(content_type, ".jpg")
        nome_arquivo = f"booking_{booking_id}_{uuid.uuid4().hex[:10]}{ext}"
        caminho = COMPROVANTES_DIR / nome_arquivo
        with open(caminho, "wb") as f:
            f.write(conteudo)

        url = f"{base_url.rstrip('/')}/static/comprovantes/{nome_arquivo}"

        pag = (
            self.db.query(Payment)
            .filter(
                Payment.booking_id == booking_id,
                Payment.tipo.in_([PaymentType.DEPOSIT, PaymentType.SINAL]),
                Payment.deleted_at.is_(None),
            )
            .first()
        )
        if not pag:
            pag = Payment(
                booking_id=booking_id,
                agendamento_id=booking.legacy_agendamento_id,
                tipo=PaymentType.DEPOSIT,
                valor=booking.deposit_amount,
                status=PaymentStatus.PENDING,
            )
            self.db.add(pag)

        pag.comprovante_url = url
        self.db.flush()
        # SYNC-PAYMENT-COREPAYMENT-01: espelho explícito (PENDING + URL).
        # Falha do espelho não bloqueia o comprovante — Payment permanece
        # a fonte primária do snapshot.
        try:
            PaymentLegacySyncService(self.db).sync_payment(pag, commit=False)
        except Exception:
            logger.warning(
                "Falha não fatal ao espelhar Payment.id=%s em CorePayment "
                "(comprovante)",
                getattr(pag, "id", None),
                exc_info=True,
            )
        self.db.commit()
        self.db.refresh(pag)
        return pag
