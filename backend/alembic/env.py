"""
Alembic environment — CoreFlow Platform.

Usa ``DATABASE_URL`` de ``app.core.config.settings`` e metadata SQLAlchemy unificada.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Importa todos os models ORM para autogenerate futuro
from app.models import *  # noqa: F401, F403
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
from app.modules.payments.domain.models import CorePayment  # noqa: F401
from app.modules.waitlist.domain.models import CoreWaitlist  # noqa: F401
from app.modules.workflow.domain.models import CoreWorkflowRun  # noqa: F401
from app.modules.workflow.domain.config_models import CoreWorkflowConfig  # noqa: F401
from app.modules.order.domain.models import CoreOrder  # noqa: F401
from app.modules.invoice.domain.models import CoreInvoice  # noqa: F401
from app.models.inventory_item import InventoryItem  # noqa: F401
from app.modules.asset.domain.models import CoreAsset  # noqa: F401
from app.modules.inventory.models import CoreInventory  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executa migrações em modo offline (SQL emitido sem engine).

    Returns:
        None
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrações em modo online com engine SQLAlchemy.

    Returns:
        None
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
