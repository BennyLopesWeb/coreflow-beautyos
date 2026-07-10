"""
Utilitário para executar migrações Alembic programaticamente.
"""
from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("alembic")


def run_alembic_upgrade(revision: str = "head") -> None:
    """
    Aplica migrações Alembic até a revision indicada.

    Usado no startup quando ``DATABASE_URL`` aponta para MySQL/produção.

    Args:
        revision: Revision alvo (default ``head``).

    Returns:
        None
    """
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    logger.info(f"Alembic upgrade → {revision}")
    command.upgrade(cfg, revision)
    print(f"✅ Alembic upgrade → {revision}")
