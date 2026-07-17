"""
R2-F3b — Catalog/Customer repositories + TD-R2-F2-002 + FF-HEX-006.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.booking.domain.entities.booking import Booking
from app.modules.booking.domain.value_objects.booking_types import (
    BookingLifecycleStatus,
    LegacyReference,
    MoneySnapshot,
    SyncStatus,
    TimeSlot,
)
from app.modules.booking.infrastructure.repositories.core_booking_repository import (
    SqlAlchemyCoreBookingRepository,
)
from app.modules.catalog.application.ports import catalog_repository as catalog_repo_mod
from app.modules.catalog.infrastructure.repositories.catalog_repository import (
    SqlAlchemyCatalogRepository,
)
from app.modules.customer.application.ports import customer_repository as customer_repo_mod
from app.modules.customer.infrastructure.adapters.customer_query_adapter import (
    SqlAlchemyCustomerQueryAdapter,
)
from app.modules.customer.infrastructure.repositories.customer_repository import (
    SqlAlchemyCustomerRepository,
)


def test_ff_hex_006_catalog_and_customer_have_repository_ports():
    """
    FF-HEX-006: Catalog + Customer expõem Protocol Repository em application/ports.
    """
    assert hasattr(catalog_repo_mod, "CatalogRepository")
    assert hasattr(customer_repo_mod, "CustomerRepository")
    ports_root = Path(__file__).resolve().parents[2] / "app" / "modules"
    assert (ports_root / "catalog" / "application" / "ports" / "catalog_repository.py").is_file()
    assert (
        ports_root / "customer" / "application" / "ports" / "customer_repository.py"
    ).is_file()


def test_catalog_repository_get_by_id(db, default_company, synced_catalog):
    """
    SqlAlchemyCatalogRepository filtra por tenant.

    Args:
        db: Sessão de teste.
        default_company: Tenant demo.
        synced_catalog: Tupla (CoreCatalog, CoreOffering).
    """
    catalog, _offering = synced_catalog
    repo = SqlAlchemyCatalogRepository(db)
    found = repo.get_by_id(catalog.id, default_company.id)
    assert found is not None
    assert found.id == catalog.id
    assert repo.get_by_id(catalog.id, company_id=99999) is None


def test_customer_repository_and_query_port(db, default_company, cliente_exemplo):
    """
    CustomerRepository + CustomerQueryPort resolvem cliente legado (FK booking).

    Args:
        db: Sessão de teste.
        default_company: Tenant demo.
        cliente_exemplo: Cliente legado.
    """
    repo = SqlAlchemyCustomerRepository(db)
    query = SqlAlchemyCustomerQueryAdapter(db)
    snap = query.get_customer(cliente_exemplo.id, default_company.id)
    assert snap.legacy_cliente_id == cliente_exemplo.id
    assert snap.active is True
    if snap.core_customer_id:
        core = repo.get_by_id(snap.core_customer_id, default_company.id)
        assert core is not None


def test_td_r2_f2_002_to_domain_uses_offering_duration(
    db, default_company, cliente_exemplo, synced_catalog
):
    """
    TD-R2-F2-002: load do aggregate usa duration_minutes do offering, não 30 fixo.

    Args:
        db: Sessão de teste.
        default_company: Tenant.
        cliente_exemplo: Cliente legado.
        synced_catalog: Catalog + offering sincronizados.
    """
    catalog, offering = synced_catalog
    offering.duration_minutes = 90
    db.add(offering)
    db.commit()
    db.refresh(offering)

    starts = datetime.utcnow() + timedelta(days=2)
    booking = Booking(
        id=None,
        company_id=default_company.id,
        customer_id=cliente_exemplo.id,
        catalog_id=catalog.id,
        offering_id=offering.id,
        time_slot=TimeSlot(starts_at=starts, ends_at=starts + timedelta(minutes=90)),
        pricing=MoneySnapshot(
            price_total=Decimal("100.00"),
            deposit_pct=Decimal("0.30"),
            deposit_amount=Decimal("30.00"),
            remaining_amount=Decimal("70.00"),
        ),
        status=BookingLifecycleStatus.PENDING,
        notes=None,
        legacy=LegacyReference(legacy_agendamento_id=None, sync_status=SyncStatus.PENDING),
        version=1,
    )
    repo = SqlAlchemyCoreBookingRepository(db)
    saved = repo.save(booking)
    db.commit()
    loaded = repo.get_by_id(saved.id, default_company.id)
    assert loaded is not None
    duration = int(
        (loaded.time_slot.ends_at - loaded.time_slot.starts_at).total_seconds() / 60
    )
    assert duration == 90


def test_customer_query_rejects_unknown(db, default_company):
    """
    CustomerQueryPort levanta ValueError para id inexistente.

    Args:
        db: Sessão de teste.
        default_company: Tenant.
    """
    query = SqlAlchemyCustomerQueryAdapter(db)
    with pytest.raises(ValueError, match="não encontrado"):
        query.get_customer(999999, default_company.id)
