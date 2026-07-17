"""
Command PromoteWaitlist — waitlist → booking + hook waitlist.promoted (P10 / R2-F4).
"""
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.core.plugin.hook_registry import hook_registry
from app.core.plugin.hooks import WaitlistPromotedPayload
from app.modules.booking.application.commands.create_booking import (
    CreateBookingCommand,
    CreateBookingHandler,
)
from app.modules.waitlist.domain.models import CoreWaitlist, CoreWaitlistStatus


@dataclass(frozen=True)
class PromoteWaitlistCommand:
    """
    Comando para promover item da fila em booking.

    Attributes:
        waitlist_id: ID ``core_waitlist``.
        company_id: Tenant.
        scheduled_at: Horário confirmado da reserva.
        correlation_id: Correlação opcional.
        notes: Observações opcionais (sobrescreve notes da fila se informado).
    """

    waitlist_id: int
    company_id: int
    scheduled_at: datetime
    correlation_id: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class PromoteWaitlistResult:
    """
    Resultado da promoção.

    Attributes:
        waitlist: Item atualizado (approved + booking_id).
        booking_id: ID do booking criado.
        hook_dispatched: Quantidade de handlers invocados (0 se flag OFF).
    """

    waitlist: CoreWaitlist
    booking_id: int
    hook_dispatched: int


class PromoteWaitlistHandler:
    """
    Handler CQRS — promove waitlist para booking e dispara hook tipado.

    Args:
        db: Sessão SQLAlchemy.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute(self, command: PromoteWaitlistCommand) -> PromoteWaitlistResult:
        """
        Cria booking, marca waitlist approved e despacha ``waitlist.promoted``.

        Args:
            command: Dados da promoção.

        Returns:
            PromoteWaitlistResult.

        Raises:
            NotFoundError: Item inexistente no tenant.
            BusinessRuleError: Status inválido para promoção.
            ValidationError: Dados insuficientes (catalog/offering/customer).
        """
        item = (
            self.db.query(CoreWaitlist)
            .filter(
                CoreWaitlist.id == command.waitlist_id,
                CoreWaitlist.company_id == command.company_id,
                CoreWaitlist.deleted_at.is_(None),
            )
            .first()
        )
        if not item:
            raise NotFoundError("Waitlist", str(command.waitlist_id))

        status = item.status
        if hasattr(status, "value"):
            status_val = status.value
        else:
            status_val = str(status)
        if status_val not in (
            CoreWaitlistStatus.WAITING.value,
            CoreWaitlistStatus.CONTACTED.value,
            "waiting",
            "contacted",
        ):
            raise BusinessRuleError("Item não está aguardando promoção")

        customer_id = item.legacy_cliente_id
        if not customer_id:
            raise ValidationError("Waitlist sem cliente legado para booking")
        if not item.catalog_id or not item.offering_id:
            raise ValidationError("Waitlist sem catalog/offering mapeados")

        booking_result = CreateBookingHandler(self.db).execute(
            CreateBookingCommand(
                customer_id=customer_id,
                catalog_id=item.catalog_id,
                offering_id=item.offering_id,
                scheduled_at=command.scheduled_at,
                company_id=command.company_id,
                notes=command.notes if command.notes is not None else item.notes,
                correlation_id=command.correlation_id,
            )
        )
        booking = booking_result.booking

        item.status = CoreWaitlistStatus.APPROVED
        item.booking_id = booking.id
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        dispatched = hook_registry.dispatch(
            "waitlist.promoted",
            WaitlistPromotedPayload(
                company_id=command.company_id,
                waitlist_id=item.id,
                booking_id=booking.id,
                customer_id=customer_id,
                catalog_id=item.catalog_id,
                offering_id=item.offering_id,
                scheduled_at=command.scheduled_at,
                correlation_id=command.correlation_id,
            ),
        )
        return PromoteWaitlistResult(
            waitlist=item,
            booking_id=booking.id,
            hook_dispatched=dispatched,
        )


def preferred_datetime(item: CoreWaitlist, override: Optional[datetime] = None) -> datetime:
    """
    Resolve datetime de agendamento a partir do item ou override.

    Args:
        item: CoreWaitlist.
        override: Horário explícito (preferencial).

    Returns:
        datetime naive para create booking.
    """
    if override is not None:
        return override.replace(tzinfo=None) if override.tzinfo else override
    pref_time = item.preferred_time or time(10, 0)
    return datetime.combine(item.preferred_date, pref_time)
