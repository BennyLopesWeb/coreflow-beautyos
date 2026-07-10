"""
Sincronização Strangler Fig — ``fila`` → ``core_waitlist``.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.fila import Fila, StatusFila
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering
from app.modules.customer.domain.models import CoreCustomer
from app.modules.waitlist.domain.models import CoreWaitlist, CoreWaitlistStatus

logger = get_logger("waitlist_sync")

_STATUS_MAP = {
    StatusFila.WAITING: CoreWaitlistStatus.WAITING,
    StatusFila.CONTACTED: CoreWaitlistStatus.CONTACTED,
    StatusFila.APPROVED: CoreWaitlistStatus.APPROVED,
    StatusFila.REJECTED: CoreWaitlistStatus.REJECTED,
    StatusFila.CANCELLED: CoreWaitlistStatus.CANCELLED,
}


class WaitlistLegacySyncService:
    """
    Sincroniza fila de espera legada para o metamodelo Waitlist.

    Idempotente — pode rodar no startup ou antes de consultas v1.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_all(self) -> int:
        """
        Sincroniza todos os itens da fila legada.

        Returns:
            Quantidade processada.
        """
        rows = self.db.query(Fila).order_by(Fila.id.asc()).all()
        count = 0
        for fila in rows:
            self._upsert(fila)
            count += 1
        self.db.commit()
        logger.info(f"Sync waitlist: {count}")
        return count

    def sync_one(self, fila_id: int) -> Optional[CoreWaitlist]:
        """
        Sincroniza um item específico da fila legada.

        Args:
            fila_id: ID ``fila``.

        Returns:
            CoreWaitlist ou None se fila não existir.
        """
        fila = self.db.query(Fila).filter(Fila.id == fila_id).first()
        if not fila:
            return None
        row = self._upsert(fila)
        self.db.commit()
        return row

    def _upsert(self, fila: Fila) -> CoreWaitlist:
        """
        Cria ou atualiza core_waitlist a partir de Fila legado.

        Args:
            fila: Registro legado.

        Returns:
            CoreWaitlist persistido.
        """
        existing = (
            self.db.query(CoreWaitlist)
            .filter(CoreWaitlist.legacy_fila_id == fila.id)
            .first()
        )
        customer = (
            self.db.query(CoreCustomer)
            .filter(CoreCustomer.legacy_cliente_id == fila.cliente_id)
            .first()
        )
        catalog = (
            self.db.query(CoreCatalog)
            .filter(CoreCatalog.legacy_tranca_id == fila.tranca_id)
            .first()
        )
        offering = (
            self.db.query(CoreOffering)
            .filter(CoreOffering.legacy_service_image_id == fila.service_image_id)
            .first()
        )
        payload = dict(
            company_id=fila.company_id or 1,
            customer_id=customer.id if customer else None,
            catalog_id=catalog.id if catalog else None,
            offering_id=offering.id if offering else None,
            preferred_date=fila.data,
            preferred_time=fila.horario_desejado,
            position=fila.posicao,
            status=_STATUS_MAP.get(fila.status, CoreWaitlistStatus.WAITING),
            booking_id=None,
            notes=fila.observacoes,
            same_day=bool(fila.mesmo_dia),
            legacy_cliente_id=fila.cliente_id,
            legacy_tranca_id=fila.tranca_id,
            legacy_service_image_id=fila.service_image_id,
            plugin_metadata={"source": "beauty", "legacy": "Fila"},
        )
        if existing:
            for key, val in payload.items():
                setattr(existing, key, val)
            return existing
        row = CoreWaitlist(legacy_fila_id=fila.id, **payload)
        self.db.add(row)
        return row
