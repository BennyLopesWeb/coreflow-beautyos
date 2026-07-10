"""
Entidade ORM Booking genérico CoreFlow.

Tabela ``core_bookings`` espelha ``agendamentos`` via Strangler Fig.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.db.enum_column import enum_values
from app.models.agendamento import ReservationStatus, StatusPagamento


class CoreBooking(Base):
    """
    Reserva genérica CoreFlow (metamodelo: Booking).

    Espelha ``Agendamento`` legado; escritas novas passam pelo handler CQRS
    que delega ao ``ReservationService`` e sincroniza este registro.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        customer_id: FK ``clientes.id``.
        catalog_id: FK ``core_catalogs.id``.
        offering_id: FK ``core_offerings.id``.
        scheduled_at: Horário solicitado.
        approved_at: Horário aprovado.
        status: Ciclo de vida da reserva.
        payment_status: Estado agregado de pagamento.
        price_total, deposit_amount, remaining_amount: Snapshot comercial.
        deposit_paid: Sinal confirmado.
        legacy_agendamento_id: FK lógica ``agendamentos.id``.
    """

    __tablename__ = "core_bookings"
    __table_args__ = (
        UniqueConstraint("legacy_agendamento_id", name="uq_core_booking_legacy_agendamento"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    catalog_id = Column(Integer, ForeignKey("core_catalogs.id"), nullable=False, index=True)
    offering_id = Column(Integer, ForeignKey("core_offerings.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        enum_values(ReservationStatus),
        default=ReservationStatus.PENDING_PAYMENT,
        nullable=False,
        index=True,
    )
    payment_status = Column(
        enum_values(StatusPagamento),
        default=StatusPagamento.PENDING_PAYMENT,
        nullable=False,
    )
    price_total = Column(Numeric(10, 2), nullable=False)
    deposit_pct = Column(Numeric(5, 4), nullable=False, default=0.30)
    deposit_amount = Column(Numeric(10, 2), nullable=False)
    remaining_amount = Column(Numeric(10, 2), nullable=False)
    deposit_paid = Column(Boolean, default=False, nullable=False)
    notes = Column(String, nullable=True)
    legacy_agendamento_id = Column(Integer, nullable=True, index=True)
    sync_status = Column(String, default="synced", nullable=False)
    version = Column(Integer, default=1, nullable=False)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    catalog = relationship("CoreCatalog")
    offering = relationship("CoreOffering")
