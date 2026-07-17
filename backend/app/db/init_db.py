"""
Script de inicialização do banco de dados
Cria todas as tabelas necessárias
"""
from app.db.base import Base
from app.db.session import engine
from app.core.config import settings
from app.models import *  # Importa todos os models para que sejam registrados
# Metamodelo CoreFlow (Sprint 1)
from app.modules.catalog.domain.models import CoreCatalog, CoreOffering  # noqa: F401
from app.modules.booking.domain.models import CoreBooking  # noqa: F401
from app.modules.scheduling.domain.models import (  # noqa: F401
    CoreLocation,
    CoreResource,
    CoreScheduleBlock,
    CoreWorker,
)
from app.modules.customer.models import CoreCustomer  # noqa: F401
from app.shared.events.outbox import CoreEventOutbox  # noqa: F401
from app.shared.events.kafka_dlq import CoreEventDlq  # noqa: F401
from app.modules.payments.domain.models import CorePayment  # noqa: F401
from app.modules.waitlist.domain.models import CoreWaitlist  # noqa: F401
from app.modules.workflow.domain.models import CoreWorkflowRun  # noqa: F401
from app.modules.workflow.domain.config_models import CoreWorkflowConfig  # noqa: F401
from app.modules.order.domain.models import CoreOrder  # noqa: F401
from app.modules.invoice.domain.models import CoreInvoice  # noqa: F401
from app.modules.asset.domain.models import CoreAsset  # noqa: F401
from app.modules.inventory.models import CoreInventory  # noqa: F401
from app.modules.push.domain.models import CoreDeviceToken  # noqa: F401
from app.modules.mobile.domain.models import CoreCanaryPromotion  # noqa: F401
from app.shared.idempotency.models import IdempotencyKey  # noqa: F401


def init_db():
    """
    Cria todas as tabelas no banco de dados
    Executa apenas se as tabelas não existirem
    """
    # Legado (companies/clientes/…) primeiro — migrations CoreFlow FK para essas tabelas.
    Base.metadata.create_all(bind=engine)

    # Migrações incrementais SQLite (legado)
    if settings.DATABASE_URL.startswith("sqlite"):
        from app.db.migrate_schema import migrate_schema
        migrate_schema()

    # MySQL: Alembic aplica/idempotenta metamodelo após base legado existir
    if settings.DATABASE_URL.startswith("mysql"):
        from app.db.alembic_runner import run_alembic_upgrade
        run_alembic_upgrade()

    bootstrap_tenant()

    print("✅ Banco de dados inicializado com sucesso!")


def bootstrap_tenant() -> None:
    """
    Garante empresa demo padrão, backfill de company_id e vínculos RBAC.

    Returns:
        None
    """
    from app.db.session import SessionLocal
    from app.modules.identity.application.identity_service import IdentityApplicationService

    db = SessionLocal()
    try:
        identity = IdentityApplicationService(db)
        company = identity.ensure_default_company()
        identity.backfill_company_id(company.id)
        identity.sync_legacy_users(company)
        print(f"✅ Tenant padrão: {company.slug} (id={company.id})")

        from app.modules.catalog.application.legacy_sync_service import LegacySyncService
        stats = LegacySyncService(db).sync_all()
        print(f"✅ Metamodelo sync: {stats}")

        from app.modules.scheduling.application.legacy_sync_service import (
            SchedulingLegacySyncService,
        )
        scheduling_stats = SchedulingLegacySyncService(db).sync_all()
        print(f"✅ Scheduling sync: {scheduling_stats}")

        from app.modules.customer.legacy_sync import CustomerLegacySyncService
        customer_stats = CustomerLegacySyncService(db).sync_all()
        print(f"✅ Customer sync: {customer_stats}")

        from app.modules.payments.application.legacy_sync_service import (
            PaymentLegacySyncService,
        )
        payment_stats = PaymentLegacySyncService(db).sync_all()
        print(f"✅ Payment sync: {payment_stats}")

        from app.modules.waitlist.application.legacy_sync_service import (
            WaitlistLegacySyncService,
        )
        waitlist_stats = WaitlistLegacySyncService(db).sync_all()
        print(f"✅ Waitlist sync: {waitlist_stats}")

        from app.modules.order.application.legacy_sync_service import OrderLegacySyncService
        order_stats = OrderLegacySyncService(db).sync_all()
        print(f"✅ Order sync: {order_stats}")

        from app.modules.invoice.application.legacy_sync_service import InvoiceLegacySyncService
        invoice_stats = InvoiceLegacySyncService(db).sync_all()
        print(f"✅ Invoice sync: {invoice_stats}")

        from app.services.inventory_seed_service import InventorySeedService
        InventorySeedService(db).ensure_default_items(company.id)

        from app.modules.asset.application.legacy_sync_service import AssetLegacySyncService
        asset_stats = AssetLegacySyncService(db).sync_all()
        print(f"✅ Asset/Inventory sync: {asset_stats}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

