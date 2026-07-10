"""
Sincronização Strangler Fig — ``financeiro`` (ENTRADA) → ``core_invoices``.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.financeiro import Financeiro, TipoMovimento
from app.modules.booking.domain.models import CoreBooking
from app.modules.invoice.domain.models import CoreInvoice, CoreInvoiceStatus
from app.modules.order.domain.models import CoreOrder

logger = get_logger("invoice_sync")


class InvoiceLegacySyncService:
    """
    Sincroniza faturas/recibos a partir de movimentos financeiros legados.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza entradas financeiras para core_invoices.

        Returns:
            Quantidade processada.
        """
        rows = (
            self.db.query(Financeiro)
            .filter(
                Financeiro.deleted_at.is_(None),
                Financeiro.tipo == TipoMovimento.ENTRADA,
            )
            .all()
        )
        count = 0
        for mov in rows:
            if self._upsert(mov):
                count += 1
        self.db.commit()
        logger.info(f"Sync invoices: {count}")
        return count

    def sync_one(self, financeiro_id: int) -> Optional[CoreInvoice]:
        """
        Sincroniza uma entrada financeira específica.

        Args:
            financeiro_id: ID ``financeiro``.

        Returns:
            CoreInvoice ou None.
        """
        mov = (
            self.db.query(Financeiro)
            .filter(Financeiro.id == financeiro_id, Financeiro.deleted_at.is_(None))
            .first()
        )
        if not mov or mov.tipo != TipoMovimento.ENTRADA:
            return None
        row = self._upsert(mov)
        self.db.commit()
        return row

    def _upsert(self, mov: Financeiro) -> Optional[CoreInvoice]:
        """
        Cria ou atualiza core_invoice a partir de Financeiro ENTRADA.

        Args:
            mov: Movimento financeiro legado.

        Returns:
            CoreInvoice persistido.
        """
        booking = None
        order = None
        if mov.agendamento_id:
            booking = (
                self.db.query(CoreBooking)
                .filter(CoreBooking.legacy_agendamento_id == mov.agendamento_id)
                .first()
            )
            order = (
                self.db.query(CoreOrder)
                .filter(CoreOrder.legacy_agendamento_id == mov.agendamento_id)
                .first()
            )

        existing = (
            self.db.query(CoreInvoice)
            .filter(CoreInvoice.legacy_financeiro_id == mov.id)
            .first()
        )
        payload = dict(
            company_id=mov.company_id or 1,
            order_id=order.id if order else None,
            booking_id=booking.id if booking else None,
            invoice_number=f"INV-{mov.id:06d}",
            description=mov.descricao,
            amount=Decimal(str(mov.valor)),
            status=CoreInvoiceStatus.PAID,
            issued_at=mov.data,
            legacy_agendamento_id=mov.agendamento_id,
        )
        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing
        row = CoreInvoice(legacy_financeiro_id=mov.id, **payload)
        self.db.add(row)
        return row
