"""
Entidades ORM do metamodelo CoreFlow — scheduling genérico.

Tabelas ``core_locations``, ``core_workers``, ``core_resources`` e
``core_schedule_blocks`` formalizam capacidade, profissionais e blocos de agenda.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.enum_column import enum_values


class ResourceType(str, enum.Enum):
    """Tipo de recurso reservável na plataforma (Resource Engine)."""

    CHAIR = "chair"
    COURT = "court"
    ROOM = "room"
    PROFESSIONAL = "professional"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    MACHINE = "machine"
    GENERIC = "generic"


class ScheduleBlockStatus(str, enum.Enum):
    """Status de um bloco genérico na agenda."""

    SCHEDULED = "scheduled"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CoreLocation(Base):
    """
    Unidade física genérica CoreFlow (metamodelo: Location).

    No plugin beauty, tipicamente um único salão por tenant (``is_default=True``).

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        name: Nome exibido (ex.: "Salão Principal").
        slug: Identificador URL-safe.
        address: Endereço estruturado (JSON).
        timezone: Fuso IANA opcional (sobrescreve o da empresa).
        active: Unidade operacional.
        is_default: Local padrão do tenant.
        plugin_metadata: Campos extras do plugin.
    """

    __tablename__ = "core_locations"
    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_core_location_company_slug"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    address = Column(JSON, default=dict)
    timezone = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    plugin_metadata = Column(JSON, default=dict)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    resources = relationship("CoreResource", back_populates="location")


class CoreWorker(Base):
    """
    Profissional genérico CoreFlow (metamodelo: Worker).

    Vincula um ``User`` a um tenant com papel operacional (owner/professional).

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        user_id: FK ``users.id``.
        display_name: Nome exibido na agenda.
        email: E-mail (desnormalizado para consultas).
        role: Papel RBAC neste tenant.
        active: Disponível para alocação.
        plugin_metadata: Campos extras do plugin.
    """

    __tablename__ = "core_workers"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_core_worker_company_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(255), nullable=False, default="professional")
    active = Column(Boolean, default=True, nullable=False)
    plugin_metadata = Column(JSON, default=dict)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CoreResource(Base):
    """
    Recurso reservável genérico CoreFlow (metamodelo: Resource).

    No plugin beauty, representa a cadeira/atendimento (capacidade 1).

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        location_id: FK ``core_locations``.
        name: Nome do recurso.
        slug: Identificador URL-safe.
        resource_type: Tipo (chair, court, room, generic).
        capacity: Vagas simultâneas (default 1).
        active: Disponível para reserva.
        is_default: Recurso padrão do local.
        plugin_metadata: Campos extras do plugin.
    """

    __tablename__ = "core_resources"
    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_core_resource_company_slug"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("core_locations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    resource_type = Column(
        enum_values(ResourceType),
        default=ResourceType.CHAIR,
        nullable=False,
    )
    capacity = Column(Integer, default=1, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    plugin_metadata = Column(JSON, default=dict)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    location = relationship("CoreLocation", back_populates="resources")


class CoreScheduleBlock(Base):
    """
    Bloco de agenda genérico CoreFlow (metamodelo: ScheduleBlock).

    Espelha ``schedules`` legado; usado pelo scheduling engine para conflitos.

    Attributes:
        id: Identificador interno.
        company_id: Tenant.
        booking_id: FK ``core_bookings`` (opcional para bloqueios manuais).
        resource_id: Recurso ocupado.
        worker_id: Profissional alocado (opcional).
        location_id: Unidade física.
        starts_at: Início do bloco.
        ends_at: Fim do bloco.
        status: Ciclo de vida do bloco.
        legacy_schedule_id: FK lógica ``schedules.id``.
    """

    __tablename__ = "core_schedule_blocks"
    __table_args__ = (
        UniqueConstraint("legacy_schedule_id", name="uq_core_schedule_legacy"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("core_bookings.id"), nullable=True, index=True)
    resource_id = Column(Integer, ForeignKey("core_resources.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("core_workers.id"), nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("core_locations.id"), nullable=False, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        enum_values(ScheduleBlockStatus),
        default=ScheduleBlockStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    legacy_schedule_id = Column(Integer, nullable=True, index=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
