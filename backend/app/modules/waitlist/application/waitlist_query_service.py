"""
Consultas read-only de Waitlist genérico CoreFlow.
"""
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.waitlist.domain.models import CoreWaitlist, CoreWaitlistStatus


class WaitlistQueryService:
    """
    Serviço de leitura para core_waitlist.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_waitlist(
        self,
        company_id: int,
        preferred_date: Optional[date] = None,
        status: Optional[CoreWaitlistStatus] = None,
    ) -> List[CoreWaitlist]:
        """
        Lista itens da fila de espera do tenant.

        Args:
            company_id: Tenant.
            preferred_date: Filtra por data desejada (opcional).
            status: Filtra por status (opcional).

        Returns:
            Lista ordenada por posição FIFO.
        """
        query = self.db.query(CoreWaitlist).filter(
            CoreWaitlist.company_id == company_id,
            CoreWaitlist.deleted_at.is_(None),
        )
        if preferred_date is not None:
            query = query.filter(CoreWaitlist.preferred_date == preferred_date)
        if status is not None:
            query = query.filter(CoreWaitlist.status == status)
        return query.order_by(
            CoreWaitlist.preferred_date.asc(),
            CoreWaitlist.position.asc(),
        ).all()

    def get_waitlist_item(self, waitlist_id: int, company_id: int) -> CoreWaitlist:
        """
        Obtém item da fila por ID com escopo de tenant.

        Args:
            waitlist_id: ID core_waitlist.
            company_id: Tenant.

        Returns:
            CoreWaitlist.

        Raises:
            NotFoundError: Se não encontrado.
        """
        row = (
            self.db.query(CoreWaitlist)
            .filter(
                CoreWaitlist.id == waitlist_id,
                CoreWaitlist.company_id == company_id,
                CoreWaitlist.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise NotFoundError("Waitlist", str(waitlist_id))
        return row
